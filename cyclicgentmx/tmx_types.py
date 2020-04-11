from __future__ import annotations
import os
from typing import Any, List, Union, Optional
from dataclasses import dataclass
from itertools import chain
import pathlib
import base64
import gzip
import zlib
import xml.etree.ElementTree as ET
from cyclicgentmx.helpers import count_types, int_or_none, float_or_none, four_bytes, clear_dict_from_none, \
    get_four_bytes


class Color:
    def __init__(self, hex_color: str) -> None:
        try:
            int(hex_color[1:], base=16)
        except ValueError:
            raise MapValidationError('"hex_color" must be str in base 16 color format')
        self.hex_color = hex_color

    @property
    def hex_color(self) -> str:
        return '#' + self.without_sharp_hex_color

    @property
    def without_sharp_hex_color(self) -> str:
        if self.a:
            colors = (self.a, self.r, self.g, self.b)
        else:
            colors = (self.r, self.g, self.b)
        argb = [hex(x)[2:].zfill(2) for x in colors]
        return ''.join(argb)

    @hex_color.setter
    def hex_color(self, value: str) -> None:
        self.__hex_color = value[1:] if value.startswith("#") else value
        if len(self.__hex_color) == 8:
            self.a, self.r, self.g, self.b = [int(value[i:i+2], base=16) for i in range(1, 9, 2)]
        else:
            self.a = None
            self.r, self.g, self.b = [int(value[i:i + 2], base=16) for i in range(1, 7, 2)]

    @property
    def a(self) -> int:
        return self.__a

    @a.setter
    def a(self, value: int) -> None:
        self.__a = value

    @property
    def r(self) -> int:
        return self.__r

    @r.setter
    def r(self, value: int) -> None:
        self.__r = value

    @property
    def g(self) -> int:
        return self.__g

    @g.setter
    def g(self, value: int) -> None:
        self.__g = value

    @property
    def b(self) -> int:
        return self.__b

    @b.setter
    def b(self, value: int) -> None:
        self.__b = value

    def __str__(self) -> str:
        return self.hex_color

@dataclass
class Property:
    name: str
    property_type: str
    value: Any

    def validate(self) -> None:
        if not all(isinstance(field, str) for field in (self.name, self.property_type)):
            raise MapStrValidationError(('name', 'property_type'))


@dataclass
class TileOffset:
    x: int
    y: int

    def validate(self) -> None:
        if not all(isinstance(field, int) for field in (self.x, self.y)):
            raise MapIntValidationError(('x', 'y'))

    def get_element(self, file_dir: str, new_file_dir: str) -> ET.Element:
        return ET.Element('tileoffset', attrib={'x': str(self.x), 'y': str(self.y)})


@dataclass
class Grid:
    orientation: str
    width: int
    height: int

    def validate(self) -> None:
        if not (isinstance(self.orientation, str) and self.orientation in ('orthogonal', 'isometric')):
            raise MapValidationError('Field orientation must be in ("orthogonal", "isometric")')
        if not all(isinstance(field, int) and field > 0 for field in (self.width, self.height)):
            raise MapIntValidationError(('width', 'height'), 0)

    def get_element(self, file_dir: str, new_file_dir: str) -> ET.Element:
        return ET.Element('grid', attrib={'orientation': self.orientation,
                                          'width': str(self.width),
                                          'height': str(self.height)})


@dataclass
class Chunk:
    x: int
    y: int
    width: int
    height: int
    tiles: List[int]

    def validate(self) -> None:
        if not all(isinstance(field, int) for field in (self.x, self.y)):
            raise MapIntValidationError(('x', 'y'),)
        if not all(isinstance(field, int) and field > 0 for field in (self.width, self.height)):
            raise MapIntValidationError(('width', 'height'), 0)
        if not (isinstance(self.tiles, list) and all(isinstance(tile, int) for tile in self.tiles)
                and len(self.tiles) == self.width * self.height):
            raise MapValidationError('Field "tiles" must be list of int type and len must be equal "width" * "height"')

    def get_element(self, file_dir: str, new_file_dir: str) -> ET.Element:
        root = ET.Element('chunk', attrib={'x': str(self.x), 'y': str(self.y),
                                           'width': str(self.width), 'height': str(self.height)})
        root.text = ''.join(map(str, self.tiles))
        return root


@dataclass
class Data:
    encoding: Optional[str]
    compression: Optional[str]
    tiles: List[int]
    chunks: List[Chunk]
    childs: Union[List[int], List[Chunk]]

    def validate(self) -> None:
        if not (self.encoding is None or isinstance(self.encoding, str) and self.encoding in ('csv', 'base64')):
            raise MapValidationError('Field "encoding" must be in ("csv", "base64")')
        if not (self.encoding != 'base64'
                or (self.compression is None
                    or isinstance(self.compression, str) and self.compression in('gzip', 'zlib'))):
            raise MapValidationError('Field "compression" must be in ("gzip", "zlib")')
        if not (isinstance(self.tiles, list) and all(isinstance(tile, int) for tile in self.tiles)):
            raise MapValidationError('Field "tiles" must be list of int type')
        if not (isinstance(self.chunks, list) and all(isinstance(chunk, Chunk) for chunk in self.chunks)):
            raise MapValidationError('Field "tiles" must be list of Chunk type')
        if not (isinstance(self.childs, list)
                and (all(isinstance(child, int) for child in self.childs) or
                     all(isinstance(child, Chunk) for child in self.childs))):
            raise MapValidationError('Field "childs" must be list of int or list of Chunk type with 0 < len < 2')
        if not (self.tiles == self.childs and not self.chunks or self.chunks == self.childs and not self.tiles):
            raise MapValidationError('Field "childs" must be equal only one "tiles" or "chunks", '
                                     'and other "tiles" or "chunks" must be None')
        for chunk in self.chunks:
            chunk.validate()

    @classmethod
    def from_element(cls, data: ET.Element) -> Data:
        encoding = data.attrib.get('encoding', None)
        compression = data.attrib.get('compression')
        tiles = []
        chunks = []
        infinite = bool(data.find('chunk') is not None)
        if infinite:
            for child in data:
                x = int_or_none(child.attrib.get('x'))
                y = int_or_none(child.attrib.get('y'))
                width = int_or_none(child.attrib.get('width'))
                height = int_or_none(child.attrib.get('height'))
                child_tiles = cls._fill_tiles(child, encoding, compression)
                child_object = Chunk(x, y, width, height, child_tiles)
                chunks.append(child_object)
            childs = chunks
        else:
            tiles = cls._fill_tiles(data, encoding, compression)
            childs = tiles
        return cls(encoding, compression, tiles, chunks, childs)

    @classmethod
    def _fill_tiles(cls, data: ET.Element, encoding: str, compression: str) -> List[int]:
        tiles = []
        if encoding is None:
            for child in data:
                tiles.append(int_or_none(child.attrib.get('gid', 0)))
        elif encoding == 'csv':
            tiles = list(map(int, data.text.strip().split(',')))
        elif encoding == 'base64':
            data = base64.b64decode(data.text.strip().encode("latin1"))
            if compression == 'gzip':
                data = gzip.decompress(data)
            elif compression == 'zlib':
                data = zlib.decompress(data)
            elif compression is not None:
                raise ValueError("Compression format {} not supported.".format(compression))
            data = zip(data[::4], data[1::4], data[2::4], data[3::4])
            tiles = list(map(four_bytes, data))
        else:
            raise ValueError("Encoding format {} not supported.". format(encoding))
        return tiles

    def _fill_text_data(self, tiles) -> str:
        if self.encoding == 'csv':
            return ','.join(map(str, tiles))
        elif self.encoding == 'base64':
            data = bytes(chain.from_iterable(map(get_four_bytes, tiles)))
            if self.compression == 'zlib':
                data = zlib.compress(data)
            elif self.compression == 'gzip':
                data = gzip.compress(data)
            return base64.b64encode(data).decode("latin1")

    def get_element(self, file_dir: str, new_file_dir: str) -> ET.Element:
        encoding: Optional[str]
        compression: Optional[str]
        tiles: List[int]
        chunks: List[Chunk]
        childs: Union[List[int], List[Chunk]]
        attrib = {
            'encoding': self.encoding,
            'compression': self.compression,
        }
        root = ET.Element('data', attrib=clear_dict_from_none(attrib))
        if self.tiles:
            if not self.encoding:
                for tile in self.tiles:
                    if tile:
                        attrib = {'gid': str(tile)}
                    else:
                        attrib = {}
                    root.append(ET.Element('tile', attrib=attrib))
            else:
                root.text = self._fill_text_data(self.tiles)
        else:
            for child in self.childs:
                child_root = ET.Element('chunk', attrib={'x': str(child.x), 'y': str(child.y),
                                                         'width': str(child.width), 'height': str(child.height)})
                child_root.text = self._fill_text_data(child.tiles)
                root.append(child_root)
        return root


@dataclass
class Image:
    format: str
    source: str
    trans: Optional[Color]
    width: int
    height: int
    data: Optional[Data]
    childs: List[Data]

    def validate(self) -> None:
        if self.data and not (isinstance(self.format, str) and self.format in ('png', 'gif', 'jpg', 'bmp')):
            raise MapValidationError('Field "format" must be in ("png", "gif", "jpg", "bmp")')
        if not isinstance(self.source, str):
            raise MapStrValidationError('source')
        if not (self.trans is None or isinstance(self.trans, Color)):
            raise MapValidationError('Field "trans" must be Color type')
        if not all(isinstance(field, int) and field > 0 for field in (self.width, self.height)):
            raise MapIntValidationError(('width', 'height'), 0)
        if not (self.data is None or isinstance(self.data, Data)):
            raise MapValidationError('Field "data" must be Data type or None')
        if not (isinstance(self.childs, list) and len(self.childs) < 2
                and all(isinstance(child, Data)
                        and self.data == child for child in self.childs)):
            raise MapValidationError('Field "childs" must be list of Data type with len < 2')

        for child in self.childs:
            child.validate()

    @classmethod
    def from_element(cls, image: ET.Element) -> Image:
        image_format = image.attrib.get('format')
        source = image.attrib.get('source')
        trans = Color(image.attrib.get('trans')) if image.attrib.get('trans', None) else None
        width = int_or_none(image.attrib.get('width'))
        height = int_or_none(image.attrib.get('height'))
        data = None
        childs = []

        for child in image:
            if child.tag == 'data':
                data = Data.from_element(child)
                childs.append(data)
        return cls(image_format, source, trans, width, height, data, childs)

    def get_element(self, file_dir: str, new_file_dir: str) -> ET.Element:
        source = os.path.relpath(os.path.normpath(os.path.join(file_dir, self.source)), start=new_file_dir)
        attrib = {'format': self.format,
                  'source': source,
                  'trans': self.trans.without_sharp_hex_color if self.trans else None,
                  'width': str(self.width),
                  'height': str(self.height)}
        root = ET.Element('image', attrib=clear_dict_from_none(attrib))
        if self.data:
            root.append(self.data.get_element(file_dir, new_file_dir))
        return root


@dataclass
class Terrain:
    name: str
    tile: str
    properties: Optional[Properties]
    childs: List[Properties]

    def validate(self) -> None:
        if not all(isinstance(field, str) for field in (self.name, self.tile)):
            raise MapStrValidationError(('name', 'tile'))
        if not (self.properties is None or isinstance(self.properties, Properties)):
            raise MapValidationError('Field "properties" must be None or Properties type')
        if not (isinstance(self.childs, list)
                and len(self.childs) < 2
                and all(isinstance(child, Properties)
                        and self.properties == child for child in self.childs)):
            raise MapValidationError('Field "childs" must be list of Properties type')
        for child in self.childs:
            child.validate()

    def get_element(self, file_dir: str, new_file_dir: str) -> ET.Element:
        root = ET.Element('terrain', attrib={'name': self.name, 'tile': self.tile})
        for child in self.childs:
            root.append(child.get_element(file_dir, new_file_dir))
        return root


@dataclass
class Object:
    id: int
    name: Optional[str]
    object_type: Optional[str]
    x: float
    y: float
    width: Optional[float]
    height: Optional[float]
    rotation: Optional[float]
    gid: Optional[int]
    visible: bool
    template: Optional[str]
    figure_type: Optional[str]
    points: List[List[float, float]]
    properties: Optional[Properties]
    childs: List[Properties]

    def validate(self) -> None:
        if not isinstance(self.id, int):
            raise MapIntValidationError(('id',))
        if not (self.gid is None or isinstance(self.gid, int)):
            raise MapIntValidationError('gid', none=True)
        if not all(isinstance(field, float) and field > 0 for field in (self.x, self.y)):
            MapFloatValidationError(('x', 'y'), 0)
        if not all(field is None or isinstance(field, float) and field > 0
                   for field in (self.width, self.height, self.rotation)):
            raise MapFloatValidationError(('width', 'height', 'rotation'), 0, none=True)
        if not all(self.field is None or isinstance(field, str)
                   for field in (self.name, self.object_type, self.template, self.figure_type)):
            raise MapStrValidationError(('name', 'object_type', 'template', 'figure_type'), none=True)
        if self.figure_type is None or self.figure_type not in ('ellipse', 'point', 'polygon', 'polyline', 'text'):
            raise MapValidationError('Field "figure_type" must be None or in ("ellipse", "point", "polygon", '
                                     '"polyline", "text")')
        if not (self.properties is None or isinstance(self.properties, Properties)):
            raise MapValidationError('Field "properties" must be None or Properties type')
        if self.visible:
            return MapValidationError('Field "visible" must be bool type')
        if not (isinstance(self.childs, list) and len(self.childs) < 2
                and all(isinstance(child, Properties) for child in self.childs)):
            raise MapValidationError('Field "childs" must be List[Properties]'
                                     ' type with len < 2')
        if self.object_type in ('polygon', 'polyline'):
            if not (isinstance(self.points, list)
                    and all(isinstance(field, list)
                            and len(field) == 2
                            and all(isinstance(f, float) for f in field) for field in self.points)):
                raise MapValidationError('Field "points" must be list of [float, float]')
        else:
            if not (isinstance(self.points, list)
                    and len(self.points) == 0):
                raise MapValidationError('Field "points" must be empty list')
        for child in self.childs:
            child.validate()

    @classmethod
    def from_element(cls, object: ET.Element) -> Object:
        object_id = object.attrib.get('id')
        name = object.attrib.get('name', None)
        object_type = object.attrib.get('type', None)
        x = float(object.attrib.get('x'))
        y = float(object.attrib.get('y'))
        width = float_or_none(object.attrib.get('width', None))
        height = float_or_none(object.attrib.get('height', None))
        rotation = float_or_none(object.attrib.get('rotation', None))
        gid = int_or_none(object.attrib.get('gid', None))
        visible = bool(int(object.attrib.get('visible', 1)))
        template = object.attrib.get('template', None)
        figure_type = None
        points = []
        properties = None
        childs = []
        for child in object:
            if child.tag == 'properties':
                properties = Properties.from_element(child)
                childs.append(properties)
            else:
                figure_type = child.tag
                points_str = child.attrib.get('points', None)
                if points_str:
                    points = points_str.split()
                    points = [list(map(float, p.split(','))) for p in points]
        return cls(object_id, name, object_type, x, y, width, height, rotation, gid, visible, template, figure_type,
                   points, properties, childs)

    def get_element(self, file_dir: str, new_file_dir: str) -> ET.Element:
        attrib = {
            'id': self.id,
            'name': self.name,
            'object_type': self.object_type,
            'x': self.x,
            'y': self.y,
            'width': str(self.width) if self.width else None,
            'height': str(self.height) if self.height else None,
            'rotation': str(self.rotation) if self.rotation else None,
            'gid': str(self.gid) if self.gid else None,
            'visible': None if self.visible else '0',
            'template': str(self.template) if self.template else None,

        }
        root = ET.Element('object', attrib=clear_dict_from_none(attrib))
        for child in self.childs:
            root.append(child.get_element(file_dir, new_file_dir))
        if self.figure_type:
            if self.points:
                points = [','.join(map(str,field)) for field in self.points]
                points = ' '.join(points)
            else:
                points = None
            child_attrib = {
                'points': points
            }
            root.append(ET.Element(self.figure_type, attrib=clear_dict_from_none(child_attrib)))
        return root


@dataclass
class Objects:
    childs: List[Object]

    def validate(self) -> None:
        if not (isinstance(self.childs, list) and all(isinstance(child, Object) for child in self.childs)):
            raise MapValidationError('Field "childs" must be list of Object')
        for child in self.childs:
            child.validate()


@dataclass
class ObjectGroup:
    id: int
    name: Optional[str]
    color: Optional[Color]
    x: Optional[int]
    y: Optional[int]
    width: Optional[int]
    height: Optional[int]
    opacity: Optional[float]
    visible: bool
    offsetx: Optional[float]
    offsety: Optional[float]
    draworder: Optional[str]
    properties: Properties
    objects: Objects
    childs: List[Union[Properties, Object]]

    def validate(self) -> None:
        if not isinstance(self.id, int):
            raise MapIntValidationError(('id'))
        if not (self.name is None or isinstance(self.name, str)):
            raise MapStrValidationError('name')
        if not(self.color is None or isinstance(self.color, Color)):
            raise MapValidationError('Field "color" must be None or Color type')
        if not all(field is None or isinstance(field, int) for field in (self.x, self.y, self.width, self.height)):
            raise MapIntValidationError(('x', 'y', 'width', 'height'), none=True)
        if not all(field is None or isinstance(field, float) for field in (self.opacity, self.offsetx, self.offsety)):
            raise MapFloatValidationError(('opacity', 'offsetx', 'offsety'), none=True)
        if not (self.offsety is None and self.offsety is None or self.offsety is not None and self.offsety is not None):
            raise MapValidationError('Fields "offsetx" and "offsety" must be None or float together')
        if self.visible:
            return MapValidationError('Field "visible" must be bool type')
        if not (self.draworder is None or self.draworder != "index"):
            return MapValidationError('Field "draworder" must be None or False')
        if not (self.properties is None or isinstance(self.properties, Properties)):
            raise MapValidationError('Field "properties" must be None or Properties type')
        if not (self.objects is None or isinstance(self.objects, Objects)):
            raise MapValidationError('Field "properties" must be None or Objects type')
        if not (isinstance(self.childs, list)
                and (all(isinstance(child, Properties) or isinstance(child, Object) for child in self.childs))):
            raise MapValidationError('Field "childs" must be list of Properties or list of Object')
        if len([child for child in self.childs if isinstance(child, Properties)]) > 1:
            raise MapValidationError('Properties type must be < 2 times in "childs"')
        for child in self.childs:
            child.validate()

    @classmethod
    def from_element(cls, objectgroup: ET.Element) -> ObjectGroup:
        objectgroup_id = int(objectgroup.attrib.get('id'))
        name = objectgroup.attrib.get('name')
        color = Color(objectgroup.attrib.get('color', None)) if objectgroup.attrib.get('color', None) else None
        x = int_or_none(objectgroup.attrib.get('x', None))
        y = int_or_none(objectgroup.attrib.get('y', None))
        width = int_or_none(objectgroup.attrib.get('width', None))
        height = int_or_none(objectgroup.attrib.get('height', None))
        opacity = float_or_none(objectgroup.attrib.get('opacity', None))
        visible = bool(int(objectgroup.attrib.get('visible', 1)))
        offsetx = float_or_none(objectgroup.attrib.get('offsetx', None))
        offsety = float_or_none(objectgroup.attrib.get('offsety', None))
        draworder = objectgroup.attrib.get('draworder', None)

        properties = None
        objects = []
        childs = []

        for child in objectgroup:
            if child.tag == 'properties':
                properties = Properties.from_element(child)
                childs.append(properties)
            elif child.tag == 'object':
                child_object = Object.from_element(child)
                objects.append(child_object)
                childs.append(child_object)
        return cls(objectgroup_id, name, color, x, y, width, height, opacity, visible,
                           offsetx, offsety, draworder, properties, Objects(objects), childs)

    def get_element(self, file_dir: str, new_file_dir: str) -> ET.Element:
        attrib = {
            'id': str(self.id),
            'name': self.name if self.name else None,
            'color': self.color.hex_color if self.color else None,
            'x': str(self.x) if self.x else None,
            'y': str(self.y) if self.y else None,
            'width': str(self.width) if self.width else None,
            'height': str(self.height) if self.height else None,
            'opacity': str(self.opacity) if self.opacity else None,
            'visible': None if self.visible else '0',
            'offsetx': str(self.offsetx) if self.offsetx else None,
            'offsety': str(self.offsety) if self.offsety else None,
            'draworder': self.draworder

        }
        root = ET.Element('objectgroup', attrib=clear_dict_from_none(attrib))
        for child in self.childs:
            root.append(child.get_element(file_dir, new_file_dir))
        return root



@dataclass
class Frame:
    tileid: int
    duration: int

    def validate(self) -> None:
        if not (isinstance(self.tileid, int) and isinstance(self.duration, int)):
            raise MapIntValidationError(('tileid', 'duration'))

    def get_element(self, file_dir: str, new_file_dir: str) -> ET.Element:
        return ET.Element('frame', attrib={'tileid': str(self.tileid), 'duration': str(self.duration)})


@dataclass
class Animation:
    childs: List[Frame]

    def validate(self) -> None:
        if not (isinstance(self.childs, list) and all(isinstance(child, Frame) for child in self.childs)):
            raise MapValidationError('Field "childs" must be list of Frame')
        for child in self.childs:
            child.validate()

    @classmethod
    def from_element(cls, animation: ET.Element) -> Animation:
        result = []
        for frame in animation:
            if frame.tag == 'frame':
                tileid = int(frame.attrib.get('tileid'))
                duration = int(frame.attrib.get('duration'))
                result.append(Frame(tileid, duration))
        return cls(result)

    def get_element(self, file_dir: str, new_file_dir: str) -> ET.Element:
        root = ET.Element('animation')
        for child in self.childs:
            root.append(child.get_element(file_dir, new_file_dir))
        return root


@dataclass
class Tile:
    id: int
    type: Optional[str]
    terrain: Optional[List[int]]
    probability: Optional[float]
    properties: Optional[Properties]
    image: Optional[Image]
    objectgroup: Optional[ObjectGroup]
    animation: Optional[Animation]
    childs: List[Union[Properties, Image, ObjectGroup, Animation]]

    def validate(self) -> None:
        if not isinstance(self.id, int):
            raise MapIntValidationError('id')
        if not (self.type is None or isinstance(self.type, str)):
            raise MapStrValidationError('type', none=True)
        if not (self.terrain is None
                or isinstance(self.terrain, list)
                and all(element is None or isinstance(element, int) for element in self.terrain)):
            raise MapValidationError('Field "terrain" must be None or list of int')
        if not (self.probability is None or isinstance(self.probability, float) and self.probability > 0):
            raise MapFloatValidationError('probability', 0)
        if not (self.image is None or isinstance(self.image, Image)):
            raise MapValidationError('Field "properties" must be None or Image type')
        if not (self.objectgroup is None or isinstance(self.objectgroup, ObjectGroup)):
            raise MapValidationError('Field "properties" must be None or ObjectGroup type')
        if not (self.animation is None or isinstance(self.animation, Animation)):
            raise MapValidationError('Field "properties" must be None or Animation type')
        if not (isinstance(self.childs, list)
                and (all(isinstance(child, Properties) and child == self.properties or
                         isinstance(child, Image) and child == self.image or
                         isinstance(child, ObjectGroup) and child == self.objectgroup or
                         isinstance(child, Animation) and child == self.animation for child in self.childs))):
            raise MapValidationError('Field "childs" must be list of (Properties or Image or ObjectGroup or Animation)')
        if not (self.properties is None or isinstance(self.properties, Properties)):
            raise MapValidationError('Field "properties" must be None or Properties type')
        if len([child for child in self.childs if isinstance(child, Properties)]) > 1:
            raise MapValidationError('Properties type must be < 2 times in "childs"')
        if len([child for child in self.childs if isinstance(child, Image)]) > 1:
            raise MapValidationError('Image type must be < 2 times in "childs"')
        for child in self.childs:
            child.validate()

    @classmethod
    def from_element(cls, tile: ET.Element) -> Tile:
        tile_id = int(tile.attrib.get('id'))
        tile_type = tile.attrib.get('type', None)
        terrain = tile.attrib.get('terrain', None)
        if terrain is not None:
            terrain = [int(element) if element else None for element in terrain.split(',')]
        probability = float_or_none(tile.attrib.get('probability', None))

        properties = None
        image = None
        objectgroup = None
        animation = None
        childs = []

        for child in tile:
            if child.tag == 'properties':
                child_object = Properties.from_element(child)
                properties = child_object
            elif child.tag == 'image':
                child_object = Image.from_element(child)
                image = child_object
            elif child.tag == 'objectgroup':
                child_object = ObjectGroup.from_element(child)
                objectgroup = child_object
            elif child.tag == 'animation':
                child_object = Animation.from_element(child)
                animation = child_object
            else:
                continue
            childs.append(child_object)
        return cls(tile_id, tile_type, terrain, probability, properties, image, objectgroup, animation, childs)

    def get_element(self, file_dir: str, new_file_dir: str) -> ET.Element:
        attrib = {
            'id': self.id,
            'type': self.type,
            'terrain': ','.join(str(t) if t is not None else '' for t in self.terrain) if self.terrain else None,
            'probability': str(self.probability) if self.probability else None
        }
        root = ET.Element('tile', attrib=clear_dict_from_none(attrib))
        for child in self.childs:
            root.append(child.get_element(file_dir, new_file_dir))
        return root


@dataclass
class WangColor:
    name: str
    color: Color
    tile: int
    probability: Optional[float]
    color_type: str

    def validation(self):
        if not isinstance(self.name, str):
            raise MapStrValidationError('name')
        if not isinstance(self.color, Color):
            raise MapValidationError('Field "color" must be Color')
        if not isinstance(self.tile, int):
            raise MapIntValidationError('tile')
        if not (self.probability is None or isinstance(self.probability, float) and self.probability > 0):
            raise MapFloatValidationError('probability', 0)
        if not self.color_type in ('wangedgecolor', 'wangcornercolor'):
            raise MapValidationError('Field "color_type must be in ("wangedgecolor", "wangcornercolor")')

    def get_element(self, file_dir: str, new_file_dir: str) -> ET.Element:
        attrib = {
            'name': self.name,
            'color': self.color.hex_color,
            'tile': str(self.tile),
            'probability': str(self.probability)
        }
        return ET.Element(self.color_type, attrib=clear_dict_from_none(attrib))


class WangID:
    def __init__(self, idstr: str) -> None:
        self.top, self.top_right, self.right, self.bottom_right, self.bottom, self.bottom_left,\
        self.left, self.top_left = 0, 0, 0, 0, 0, 0, 0, 0
        self.__ids = (self.top, self.top_right, self.right, self.bottom_right,
                      self.bottom, self.bottom_left, self.left, self.top_left)
        self.idstr = idstr

    @property
    def idstr(self) -> str:
        idstr = [hex(x)[2:].zfill(2) for x in self.__ids]
        return '0x{}{}{}{}{}{}{}{}'.format(*idstr)

    @idstr.setter
    def idstr(self, value: str) -> None:
        self.__idstr = value[2:].zfill(8)
        self.ids = [int(i, base=16) for i in list(self.__idstr)]


@dataclass
class WangTile:
    tileid: int
    wangid: WangID

    def validation(self):
        if not isinstance(self.tileid, int):
            raise MapIntValidationError('taleid')
        if not isinstance(self.wangid, WangID):
            raise MapValidationError('Field wangid must be WangID type')

    def get_element(self, file_dir: str, new_file_dir: str) -> ET.Element:
        return ET.Element('wangtile', attrib={'tileid': str(self.tileid), 'wangid': self.wangid.idstr})


@dataclass
class WangSet:
    name: str
    tile: int
    wangcornercolors: List[WangColor]
    wangedgecolor: List[WangColor]
    wangtiles: List[WangTile]
    childs: List[Union[WangColor, WangTile]]

    def validate(self) -> None:
        if not isinstance(self.name, str):
            raise MapStrValidationError('name')
        if not (isinstance(self.tile, int) and self.tile > -2):
            raise MapIntValidationError('tile', -2)
        if not (isinstance(self.wangcornercolors, list)
                and all(isinstance(child, WangColor) for child in self.wangcornercolors)):
            raise MapValidationError('Field "wangcornercolors" must be list of WangColor')
        if not (isinstance(self.wangedgecolor, list)
                and all(isinstance(child, WangColor) for child in self.wangedgecolor)):
            raise MapValidationError('Field "wangedgecolor" must be list of WangColor')
        if not (isinstance(self.wangtiles, list)
                and all(isinstance(child, WangTile) for child in self.wangtiles)):
            raise MapValidationError('Field "wangtiles" must be list of WangTile')
        if not (isinstance(self.childs, list)
                and (all(isinstance(child, WangColor) or
                         isinstance(child, WangTile) for child in self.childs))):
            raise MapValidationError('Field "childs" must be list of (WangColor or WangTile)')
        for child in self.childs:
            child.validation()

    def get_element(self, file_dir: str, new_file_dir: str) -> ET.Element:
        root = ET.Element('wangset', attrib={'name': str(self.name), 'tile': str(self.tile)})
        for child in self.childs:
            root.append(child.get_element(file_dir, new_file_dir))
        return root


@dataclass
class TerrainTypes:
    childs: List[Terrain]

    def validate(self) -> None:
        if not (isinstance(self.childs, list) and all(isinstance(child, Terrain) for child in self.childs)):
            raise MapValidationError('Field "childs" must be list of Terrain')
        for child in self.childs:
            child.validate()

    @classmethod
    def from_element(cls, terraintypes: ET.Element) -> TerrainTypes:
        result = []
        for terrain in terraintypes:
            if terrain.tag == 'terrain':
                name = terrain.attrib.get("name")
                tile = terrain.attrib.get("tile")
                properties = None
                childs = []
                for terrain_properties in terrain:
                    if terrain_properties.tag == 'properties':
                        properties = Properties.from_element(terrain_properties)
                        childs.append(properties)
                    else:
                        continue
                result.append(Terrain(name, tile, properties, childs))
        return cls(result)

    def get_element(self, file_dir: str, new_file_dir: str) -> ET.Element:
        root = ET.Element('terraintypes')
        for child in self.childs:
            root.append(child.get_element(file_dir, new_file_dir))
        return root


@dataclass
class Properties:
    childs: List[Property]

    def validate(self) -> None:
        if not (isinstance(self.childs, list) and all(isinstance(child, Property) for child in self.childs)):
            raise MapValidationError('Field "childs" must be list of Property')
        for child in self.childs:
            child.validate()

    @classmethod
    def from_element(cls, properties: ET.Element) -> Properties:
        result = []
        for prop in properties:
            prop_type = prop.attrib.get('type', 'string')
            if prop_type == 'int':
                value = int(prop.attrib.get('value'))
            elif prop_type == 'float':
                value = float(prop.attrib.get('value'))
            elif prop_type == 'bool':
                value = prop.attrib.get('value') == 'true'
            elif prop_type == 'color':
                value = Color(prop.attrib.get('value'))
            elif prop_type == 'file':
                value = prop.attrib.get('value')
            else:
                continue
            result.append(Property(prop.attrib.get('name'),
                                   prop_type,
                                   value
                                   )
                          )
        return cls(result)

    def get_element(self, file_dir: str, new_file_dir: str) -> ET.Element:
        root = ET.Element('properties')
        for child in self.childs:
            prop_type = child.property_type
            if prop_type == 'bool':
                value = 'true' if child.value else 'false'
            elif prop_type == 'color':
                value = child.value.hex_color()
            else:
                value = str(child.value)
            child_element = ET.Element('property', attrib={'name': child.name, 'type': child.property_type, 'value': value})
            root.append(child_element)
        return root


@dataclass
class WangSets:
    childs: List[WangSet]

    def validate(self) -> None:
        if not (isinstance(self.childs, list) and all(isinstance(child, WangSet) for child in self.childs)):
            raise MapValidationError('Field "childs" must be list of WangSet')
        for child in self.childs:
            child.validate()

    @classmethod
    def from_element(cls, wangsets: ET.Element) -> WangSets:
        result = []
        for wangset in wangsets:
            if wangset.tag == 'wangset':
                name = wangset.attrib.get('name', None)
                tile = int_or_none(wangset.attrib.get('tile', None))
                wangcornercolors = []
                wangedgecolor = []
                wangtiles = []
                childs = []
                for child in wangset:
                    if child.tag == 'wangcornercolors':
                        name = child.attrib.get('name', None)
                        color = Color(child.attrib.get('color', None)) if child.attrib.get('color', None) else None
                        child_tile = int(child.attrib.get('tile', None))
                        probability = float_or_none(child.attrib.get('probability', None))
                        wangcolor = WangColor(name, color, child_tile, probability, 'wangcornercolor')
                        wangcornercolors.append(wangcolor)
                        childs.append(wangcolor)
                    elif child.tag == 'wangedgecolor':
                        name = child.attrib.get('name', None)
                        color = Color(child.attrib.get('color', None)) if child.attrib.get('color', None) else None
                        child_tile = int(child.attrib.get('tile', None))
                        probability = float_or_none(child.attrib.get('probability', None))
                        wangcolor = WangColor(name, color, child_tile, probability, 'wangedgecolor')
                        wangedgecolor.append(wangcolor)
                        childs.append(wangcolor)
                    elif child.tag == 'wangtile':
                        tileid = int(child.attrib.get('tileid', None))
                        wangid = child.attrib.get('wangid', None)
                        if wangid:
                            wangid = WangID(wangid)
                        wangtile = WangTile(tileid, wangid)
                        wangtiles.append(wangtile)
                        childs.append(wangtile)
                result.append(WangSet(name, tile, wangcornercolors, wangedgecolor, wangtiles, childs))
        return cls(result)

    def get_element(self, file_dir: str, new_file_dir: str) -> ET.Element:
        root = ET.Element('wangsets')
        for child in self.childs:
            root.append(child.get_element(file_dir, new_file_dir))
        return root


@dataclass
class TileSet:
    firstgid: int
    source: Optional[str]
    name: str
    tilewidth: int
    tileheight: int
    spacing: Optional[int]
    margin: Optional[int]
    tilecount: int
    columns: int
    version: str
    tiledversion: str
    tileoffset: Optional[TileOffset]
    grid: Optional[Grid]
    properties: Optional[Properties]
    image: Image
    terraintypes: Optional[TerrainTypes]
    tiles: List[Tile]
    wangsets: Optional[WangSets]
    childs: List[Union[TileOffset, Grid, Properties, Image, TerrainTypes, Tile, WangSets]]

    def validate(self) -> None:
        if not all(isinstance(field, int) and field > 0
                   for field in (self.firstgid, self.tilewidth, self.tileheight, self.tilecount, self.columns)):
            raise MapIntValidationError(('firstgid', 'tilewidth', 'tileheight', 'tilecount', 'columns'), 0)
        if not all(field is None or isinstance(field, int) and field > 0
                   for field in (self.spacing, self.margin)):
            raise MapIntValidationError('spacing', 'margin', 0, none=True)
        if not all(isinstance(field, str) for field in (self.name, self.version, self.tiledversion)):
            raise MapStrValidationError(('name', 'version', 'tiledversion'))
        if not (self.tileoffset is None or isinstance(self.tileoffset, TileOffset)):
            raise MapValidationError('Field "tileoffset" must be TileOffset type')
        if len([child for child in self.childs if isinstance(child, TileOffset)]) > 1:
            raise MapValidationError('Image type must be < 2 times in "childs"')
        if not (self.grid is None or isinstance(self.grid, Grid)):
            raise MapValidationError('Field "grid" must be None or Grid type')
        if len([child for child in self.childs if isinstance(child, Grid)]) > 1:
            raise MapValidationError('Image type must be < 2 times in "childs"')
        if not (self.terraintypes is None or isinstance(self.terraintypes, TerrainTypes)):
            raise MapValidationError('Field "terraintypes" must be None or TerrainTypes type')
        if len([child for child in self.childs if isinstance(child, TerrainTypes)]) > 1:
            raise MapValidationError('Image type must be < 2 times in "childs"')
        if not (isinstance(self.tiles, list) and all(isinstance(tile, Tile) for tile in self.tiles)):
            raise MapValidationError('Field "tiles" must be list of Tile type')
        if len([child for child in self.childs if isinstance(child, TerrainTypes)]) > 1:
            raise MapValidationError('Image type must be < 2 times in "childs"')
        if not (self.wangsets is None or isinstance(self.wangsets, WangSets)):
            raise MapValidationError('Field "wangsets" must be None or WangSets type')
        if not (isinstance(self.childs, list)
                and (all(isinstance(child, TileOffset) and self.tileoffset == child or
                         isinstance(child, Grid) and self.grid == child or
                         isinstance(child, Properties) and self.properties == child or
                         isinstance(child, Image) and self.image == child or
                         isinstance(child, TerrainTypes) and self.terraintypes == child or
                         isinstance(child, Tile) or
                         isinstance(child, WangSets) and self.wangsets == child for child in self.childs))):
            raise MapValidationError('Field "childs" must be list of (TileOffset or Grid or Properties or Image'
                                     ' or TerrainTypes or Tile or WangSets)')
        if not (self.properties is None or isinstance(self.properties, Properties)):
            raise MapValidationError('Field "properties" must be None or Properties type')
        if not (self.image is None or isinstance(self.image, Image)):
            raise MapValidationError('Field "image" must be None or Image type')
        common = count_types(self.childs)
        for type_count in common:
            if common[type_count] > 1 and type_count != Tile:
                raise MapValidationError('{} can be maximum only once in "childs"'.format(type_count))
        for child in self.childs:
            child.validate()

    @classmethod
    def from_element(cls, tileset: ET.Element, file_dir) -> TileSet:
        firstgid = int(tileset.attrib.get('firstgid'))
        source = tileset.attrib.get('source', None)
        if source:
            source_with_path = pathlib.PurePath(file_dir, source).as_posix()
            tileset_tree = ET.parse(source_with_path)
            tileset_root = tileset_tree.getroot()
        else:
            tileset_root = tileset
        name = tileset_root.attrib.get('name')
        tilewidth = int(tileset_root.attrib.get('tilewidth'))
        tileheight = int(tileset_root.attrib.get('tileheight'))
        spacing = int_or_none(tileset_root.attrib.get('spacing', None))
        margin = int_or_none(tileset_root.attrib.get('margin', None))
        tilecount = int_or_none(tileset_root.attrib.get('tilecount'))
        columns = int_or_none(tileset_root.attrib.get('columns'))

        version = tileset_root.attrib.get('version', None)
        tiledversion = tileset_root.attrib.get('tiledversion', None)

        tileoffset = None
        grid = None
        properties = None
        image = None
        terraintypes = None
        tiles = []
        wangsets = None
        childs = []
        for child in tileset_root:
            if child.tag == 'tileoffset':
                x = int_or_none(child.attrib.get('x'))
                y = int_or_none(child.attrib.get('y'))
                child_object = TileOffset(x, y)
                tileoffset = child_object
            elif child.tag == 'grid':
                orientation = child.attrib.get('orientation')
                width = int_or_none(child.attrib.get('width'))
                height = int_or_none(child.attrib.get('height'))
                child_object = Grid(orientation, width, height)
                grid = child_object
            elif child.tag == 'properties':
                child_object = Properties.from_element(child)
                properties = child_object
            elif child.tag == 'image':
                child_object = Image.from_element(child)
                image = child_object
            elif child.tag == 'terraintypes':
                child_object = TerrainTypes.from_element(child)
                terraintypes = child_object
            elif child.tag == 'tile':
                child_object = Tile.from_element(child)
                tiles.append(child_object)
            elif child.tag == 'wangsets':
                child_object = WangSets.from_element(child)
                wangsets = child_object
            else:
                continue
            childs.append(child_object)

        return cls(firstgid, source, name, tilewidth, tileheight, spacing, margin, tilecount, columns,
                       version, tiledversion, tileoffset, grid, properties, image, terraintypes,
                       tiles, wangsets, childs)

    def get_element(self, file_dir: str, new_file_dir: str) -> ET.Element:
        if self.source:
            source = os.path.relpath(os.path.normpath(os.path.join(file_dir, self.source)), start=new_file_dir)
            attrib = {
                'firstgid': str(self.firstgid),
                'source': source,
            }
        else:
            attrib = {
                'firstgid': str(self.firstgid),
                'source': self.source,
                'name': self.name,
                'tilewidth': str(self.tilewidth),
                'tileheight': str(self.tileheight),
                'spacing': str(self.spacing) if self.spacing else None,
                'margin': str(self.margin) if self.spacing else None,
                'tilecount': str(self.tilecount),
                'columns': str(self.columns),
                'version': self.version,
                'tiledversion': self.tiledversion
            }
        root = ET.Element('tileset', attrib=clear_dict_from_none(attrib))
        if not self.source:
            for child in self.childs:
                root.append(child.get_element(file_dir, new_file_dir))
        return root


@dataclass
class Layer:
    id: int
    name: str
    x: Optional[int]
    y: Optional[int]
    width: int
    height: int
    opacity: Optional[float]
    visible: bool
    offsetx: Optional[float]
    offsety: Optional[float]
    properties: Optional[Properties]
    data: Data  # validate Data len(tiles) if not infinite map?
    childs: List[Union[Properties, Data]]

    def validate(self) -> None:
        if not (isinstance(self.id, int) and self.id > 0):
            raise MapIntValidationError("id", 0)
        if not isinstance(self.name, str):
            raise MapValidationError('Field "name" must be str')
        if not all(field is None or isinstance(field, int) for field in (self.x, self.y)):
            raise MapValidationError('Fields "x" and "y" must be None or int type')
        if not all(isinstance(field, int) and field > 0 for field in (self.width, self.height)):
            raise MapIntValidationError(('width', 'height'), 0)
        if not all(field is None or isinstance(field, float) for field in (self.opacity, self.offsetx, self.offsety)):
            raise MapFloatValidationError(('opacity', 'offsetx', 'offsety'), none=True)
        if not (self.offsety is None and self.offsety is None or self.offsety is not None and self.offsety is not None):
            raise MapValidationError('Fields "offsetx" and "offsety" must be None or float together')
        if not isinstance(self.visible, bool):
            return MapValidationError('Field "visible" must be bool type')
        if not (isinstance(self.childs, list)
                and (all(isinstance(child, Properties) or
                         isinstance(child, Data) for child in self.childs))):
            raise MapValidationError('Field "childs" must be list of (Properties or Data)')
        if not (self.properties is None or isinstance(self.properties, Properties)):
            raise MapValidationError('Field "properties" must be None or Properties type')
        if len([child for child in self.childs if isinstance(child, Properties)]) > 1:
            raise MapValidationError('Properties type must be < 2 times in "childs"')
        if not isinstance(self.data, Data):
            raise MapValidationError('Field "data" must be Data type')
        if len([child for child in self.childs if isinstance(child, Data)]) > 1:
            raise MapValidationError('Properties type must be < 2 times in "childs"')
        for child in self.childs:
            child.validate()

    @classmethod
    def from_element(cls, layer: ET.Element) -> Layer:
        layer_id = int_or_none(layer.attrib.get('id', None))
        name = layer.attrib.get('name', None)
        x = int_or_none(layer.attrib.get('x', None))
        y = int_or_none(layer.attrib.get('y', None))
        width = int_or_none(layer.attrib.get('width', None))
        height = int_or_none(layer.attrib.get('height', None))
        opacity = float_or_none(layer.attrib.get('opacity', None))
        visible = bool(int(layer.attrib.get('visible', 1)))
        offsetx = float_or_none(layer.attrib.get('offsetx', None))
        offsety = float_or_none(layer.attrib.get('offsety', None))

        properties = None
        data = None
        childs = []

        for child in layer:
            if child.tag == 'properties':
                properties = Properties.from_element(child)
                childs.append(properties)
            elif child.tag == 'data':
                data = Data.from_element(child)
                childs.append(data)
        return cls(layer_id, name, x, y, width, height, opacity, visible,
                     offsetx, offsety, properties, data, childs)

    def get_element(self, file_dir: str, new_file_dir: str) -> ET.Element:
        attrib = {
            'id': str(self.id),
            'name': self.name,
            'x': str(self.x) if self.x else None,
            'y': str(self.y) if self.y else None,
            'width': str(self.width),
            'height': str(self.height),
            'opacity': str(self.opacity) if self.opacity else None,
            'visible': '0' if not self.visible else None,
            'offsetx': str(self.offsetx) if self.offsetx else None,
            'offsety': str(self.offsety) if self.offsety else None
        }
        root = ET.Element('layer', attrib=clear_dict_from_none(attrib))
        for child in self.childs:
            root.append(child.get_element(file_dir, new_file_dir))
        return root


@dataclass
class ImageLayer:
    id: int
    name: str
    offsetx: Optional[float]
    offsety: Optional[float]
    x: Optional[int]
    y: Optional[int]
    opacity: Optional[float]
    visible: bool
    properties: Properties
    image: Image
    childs: List[Union[Properties, Image]]

    def validate(self) -> None:
        if not (isinstance(self.id, int) and self.id > 0):
            raise MapIntValidationError("id", 0)
        if not isinstance(self.name, str):
            raise MapValidationError('Field "name" must be str')
        if not all(field is None or isinstance(field, int) for field in (self.x, self.y)):
            raise MapIntValidationError(('x', 'y'), none=True)
        if not all(field is None or isinstance(field, float) for field in (self.opacity, self.offsetx, self.offsety)):
            raise MapFloatValidationError(('opacity', 'offsetx', 'offsety'), none=True)
        if not (self.offsety is None and self.offsety is None or self.offsety is not None and self.offsety is not None):
            raise MapValidationError('Fields "offsetx" and "offsety" must be None or float together')
        if not isinstance(self.visible, bool):
            return MapValidationError('Field "visible" must be bool type')
        if not (isinstance(self.childs, list)
                and (all(isinstance(child, Properties) or
                         isinstance(child, Image) for child in self.childs))):
            raise MapValidationError('Field "childs" must be list of (Properties or Image)')
        if not (self.properties is None or isinstance(self.properties, Properties)):
            raise MapValidationError('Field "properties" must be None or Properties type')
        if len([child for child in self.childs if isinstance(child, Properties)]) > 1:
            raise MapValidationError('Properties type must be < 2 times in "childs"')
        if not (self.image is None or isinstance(self.image, Image)):
            raise MapValidationError('Field "image" must be None or Image type')
        if len([child for child in self.childs if isinstance(child, Image)]) > 1:
            raise MapValidationError('Image type must be < 2 times in "childs"')
        for child in self.childs:
            child.validate()

    @classmethod
    def from_element(cls, layer: ET.Element) -> ImageLayer:
        imagelayer_id = int_or_none(layer.attrib.get('id', None))
        name = layer.attrib.get('name', None)
        offsetx = float_or_none(layer.attrib.get('offsetx', None))
        offsety = float_or_none(layer.attrib.get('offsety', None))
        x = int_or_none(layer.attrib.get('x', None))
        y = int_or_none(layer.attrib.get('y', None))
        opacity = float_or_none(layer.attrib.get('opacity', None))
        visible = bool(int(layer.attrib.get('visible', 1)))

        properties = None
        image = None
        childs = []

        for child in layer:
            if child.tag == 'properties':
                properties = Properties.from_element(child)
                childs.append(properties)
            elif child.tag == 'image':
                image = Image.from_element(child)
                childs.append(image)
        return cls(imagelayer_id, name, offsetx, offsety, x, y, opacity, visible, properties, image, childs)

    def get_element(self, file_dir: str, new_file_dir: str) -> ET.Element:
        attrib = {
            'id': str(self.id),
            'name': self.name,
            'x': str(self.x) if self.x else None,
            'y': str(self.y) if self.y else None,
            'opacity': str(self.opacity) if self.opacity else None,
            'visible': '0' if not self.visible else None,
            'offsetx': str(self.offsetx) if self.offsetx else None,
            'offsety': str(self.offsety) if self.offsety else None
        }
        root = ET.Element('imagelayer', attrib=clear_dict_from_none(attrib))
        for child in self.childs:
            root.append(child.get_element(file_dir, new_file_dir))
        return root


@dataclass
class Group:
    id: int
    name: str
    offsetx: Optional[float]
    offsety: Optional[float]
    opacity: Optional[float]
    visible: bool
    properties: Properties
    layers: List[Layer]
    objectgroups: List[ObjectGroup]
    imagelayers: List[ImageLayer]
    groups: List[Group]
    childs: List[Properties, Layer, ObjectGroup, ImageLayer, Group]

    def validate(self) -> None:
        if not (isinstance(self.id, int) and self.id > 0):
            raise MapIntValidationError("id", 0)
        if not isinstance(self.name, str):
            raise MapValidationError('Field "name" must be str')
        if not all(field is None or isinstance(field, float) for field in (self.opacity, self.offsetx, self.offsety)):
            raise MapFloatValidationError(('opacity', 'offsetx', 'offsety'), none=True)
        if not (self.offsety is None and self.offsety is None or self.offsety is not None and self.offsety is not None):
            raise MapValidationError('Fields "offsetx" and "offsety" must be None or float together')
        if not isinstance(self.visible, bool):
            return MapValidationError('Field "visible" must be bool type')
        if not all(isinstance(layer, Layer) for layer in self.layers):
            raise MapValidationError('Field "layers" must be list of Layer')
        if not all(isinstance(objectgroup, ObjectGroup) for objectgroup in self.objectgroups):
            raise MapValidationError('Field "objectgroups" must be list of ObjectGroup type')
        if not all(isinstance(imagelayer, ImageLayer) for imagelayer in self.imagelayers):
            raise MapValidationError('Field "imagelayers" must be None or ImageLayer type')
        if not all(isinstance(group, Group) for group in self.groups):
            raise MapValidationError('Field "groups" must be None or Group type')
        if not (isinstance(self.childs, list)
                and (all(isinstance(child, Properties) or
                         isinstance(child, Layer) or
                         isinstance(child, ObjectGroup) or
                         isinstance(child, ImageLayer) or
                         isinstance(child, Group) for child in self.childs))):
            raise MapValidationError('Field "childs" must be list of (Properties or Layer or ObjectGroup or ImageLayer'
                                     ' or Group)')
        if not (self.properties is None or isinstance(self.properties, Properties)):
            raise MapValidationError('Field "properties" must be None or Properties type')
        if len([child for child in self.childs if isinstance(child, Properties)]) > 1:
            raise MapValidationError('Properties type must be < 2 times in "childs"')
        for child in self.childs:
            child.validate()
    @classmethod
    def from_element(cls, group: ET.Element) -> Group:
        group_id = int_or_none(group.attrib.get('id', None))
        name = group.attrib.get('name', None)
        offsetx = float_or_none(group.attrib.get('offsetx', None))
        offsety = float_or_none(group.attrib.get('offsety', None))
        opacity = float_or_none(group.attrib.get('opacity', None))
        visible = bool(int(group.attrib.get('visible', 1)))

        properties = None
        group_layers = []
        layers = []
        objectgroups = []
        imagelayers = []
        groups = []
        childs = []

        for child in group:
            if child.tag == 'properties':
                child_object = Properties.from_element(child)
                properties = child_object
            elif child.tag == 'layer':
                child_object = Layer.from_element(child)
                layers.append(child_object)
                group_layers.append(child_object)
            elif child.tag == 'objectgroup':
                child_object = ObjectGroup.from_element(child)
                objectgroups.append(child_object)
                group_layers.append(child_object)
            elif child.tag == 'imagelayer':
                child_object = ImageLayer.from_element(child)
                imagelayers.append(child_object)
                group_layers.append(child_object)
            elif child.tag == 'group':
                child_object = cls.from_element(child)
                groups.append(child_object)
                group_layers.append(child_object)
            else:
                continue
            childs.append(child_object)
        return cls(group_id, name, offsetx, offsety, opacity, visible, properties,
                     layers, objectgroups, imagelayers, groups, childs)

    def get_element(self, file_dir: str, new_file_dir: str) -> ET.Element:
        attrib = {
            'id': str(self.id),
            'name': self.name,
            'opacity': str(self.opacity) if self.opacity else None,
            'visible': '0' if not self.visible else None,
            'offsetx': str(self.offsetx) if self.offsetx else None,
            'offsety': str(self.offsety) if self.offsety else None
        }
        root = ET.Element('group', attrib=clear_dict_from_none(attrib))
        for child in self.childs:
            root.append(child.get_element(file_dir, new_file_dir))
        return root


class MapError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message

    def __str__(self) -> str:
        return self.message


class MapValidationError(MapError):
    pass


class MapIntValidationError(MapValidationError):
    def __init__(self, fields, left: int = None, right: int = None, none: bool = False) -> None:
        if isinstance(fields, str):
            self.message = 'Field ' + str(fields)
        else:
            try:
                len(fields)
                self.message = 'Fields ' + str(fields)[1:-1]
            except TypeError:
                self.message = 'Field ' + str(fields)
        if none:
            self.message += ' must be None or int type'
        else:
            self.message += ' must be int type'
        if left is not None or right is not None:
            self.message += ' and '
            if left is not None:
                int(left)
                self.message += str(left) + ' < x'
            else:
                self.message += 'x'
            if right is not None:
                self.message += ' < ' + str(right)


class MapFloatValidationError(MapValidationError):
    def __init__(self, fields, left: float = None, right: float = None, none: bool = False) -> None:
        if isinstance(fields, str):
            self.message = 'Field ' + str(fields)
        else:
            try:
                len(fields)
                self.message = 'Fields ' + str(fields)[1:-1]
            except TypeError:
                self.message = 'Field ' + str(fields)
        if none:
            self.message += ' must be None or float type'
        else:
            self.message += ' must be float type'
        if left or right:
            self.message += ' and '
            if left:
                float(left)
                self.message += str(left) + ' < x'
            else:
                self.message += 'x'
            if right:
                self.message += ' < ' + str(right)


class MapStrValidationError(MapValidationError):
    def __init__(self, fields, none: bool = False) -> None:
        if isinstance(fields, str):
            self.message = 'Field ' + str(fields)
        else:
            try:
                len(fields)
                self.message = 'Fields ' + str(fields)[1:-1]
            except TypeError:
                self.message = 'Field ' + str(fields)
        if none:
            self.message += ' must be None or str type'
        else:
            self.message += ' must be str type'
