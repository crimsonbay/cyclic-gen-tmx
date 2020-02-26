from __future__ import annotations
from typing import Any, List, Union, Optional
from dataclasses import dataclass
from cyclicgentmx.helpers import count_types


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

    def validate(self):
        if not all(isinstance(field, str) for field in (self.name, self.property_type)):
            raise MapStrValidationError(('name', 'property_type'))


@dataclass
class TileOffset:
    x: int
    y: int

    def validate(self):
        if not all(isinstance(field, int) for field in (self.x, self.y)):
            raise MapIntValidationError(('x', 'y'))


@dataclass
class Grid:
    orientation: str
    width: int
    height: int

    def validate(self):
        if not (isinstance(self.orientation, str) and self.orientation in ('orthogonal', 'isometric')):
            raise MapValidationError('Field orientation must be in ("orthogonal", "isometric")')
        if not all(isinstance(field, int) and field > 0 for field in (self.width, self.height)):
            raise MapIntValidationError(('width', 'height'), 0)


@dataclass
class Chunk:
    x: int
    y: int
    width: int
    height: int
    tiles: List[int]

    def validate(self):
        if not all(isinstance(field, int) and field > 0 for field in (self.x, self.y, self.width, self.height)):
            raise MapIntValidationError(('x', 'y', 'width', 'height'), 0)
        if not (isinstance(self.tiles, list) and all(isinstance(tile, int) for tile in self.tiles)
                and len(self.tiles) != self.width * self.height):
            raise MapValidationError('Field "tiles" must be list of int type and len must be equal "width" * "height"')


@dataclass
class Data:
    encoding: str
    compression: str
    tiles: List[int]
    chunks: List[Chunk]
    childs: Union[List[int], List[Chunk]]

    def validate(self):
        if not (isinstance(self.encoding, str) and self.encoding in('csv', 'base64')):
            raise MapValidationError('Field "encoding" must be in ("csv", "base64")')
        if not (isinstance(self.compression, str) and self.compression in('csv', 'base64')):
            raise MapValidationError('Field "compression" must be in ("gzip", "zlib")')
        if not (isinstance(self.tiles, list) and all(isinstance(tile, int) for tile in self.tiles)):
            raise MapValidationError('Field "tiles" must be list of int type')
        if not (isinstance(self.chunks, list) and all(isinstance(chunk, Chunk) for chunk in self.chunks)):
            raise MapValidationError('Field "tiles" must be list of Chunk type')
        if not (isinstance(self.childs, list) and 0 < len(self.childs) < 2
                and (all(isinstance(child, int) for child in self.childs) or
                     all(isinstance(child, Chunk) for child in self.childs))):
            raise MapValidationError('Field "childs" must be list of int or list of Chunk type with 0 < len < 2')
        if not (self.tiles == self.childs and not self.chunks or self.chunks == self.childs and not self.tiles):
            raise MapValidationError('Field "childs" must be equal only one "tiles" or "chunks", '
                                     'and other "tiles" or "chunks" must be None')
        if self.chunks:
            self.chunks.validate()


@dataclass
class Image:
    format: str
    source: str
    trans: Optional[Color]
    width: int
    height: int
    data: Optional[Data]
    childs: List[Data]

    def validate(self):
        if self.data and not (isinstance(self.format, str) and self.format in ('png', 'gif', 'jpg', 'bmp')):
            raise MapValidationError('Field "format" must be in ("png", "gif", "jpg", "bmp")')
        if not isinstance(self.source, str):
            raise MapStrValidationError('source')
        if not (self.trans is None or isinstance(self.trans, Color)):
            raise MapValidationError('Field "source" must be Color type')
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


@dataclass
class Terrain:
    name: str
    tile: str
    properties: Optional[Properties]
    childs: List[Properties]

    def validate(self):
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


@dataclass
class Object:
    id: int
    name: Optional[str]
    type: Optional[str]
    x: float
    y: float
    width: Optional[float]
    height: Optional[float]
    rotation: Optional[float]
    gid: Optional[int]
    visible: Optional[bool]
    template: Optional[str]
    child_type: Optional[str]
    properties: Optional[Properties]
    childs: List[Properties]

    def validate(self):
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
                   for field in (self.name, self.type, self.template, self.child_type)):
            raise MapStrValidationError(('name', 'type', 'template', 'child_type'), none=True)
        if self.child_type is None or self.child_type not in ('ellipse', 'point', 'polygon', 'polyline', 'text'):
            raise MapValidationError('Field "child_type" must be None or in ("ellipse", "point", "polygon", '
                                     '"polyline", "text")')
        if not (self.properties is None or isinstance(self.properties, Properties)):
            raise MapValidationError('Field "properties" must be None or Properties type')
        if self.visible:
            return MapValidationError('Field "visible" must be None or False')
        if not (isinstance(self.childs, list) and len(self.childs) < 2
                and all(isinstance(child, Properties) for child in self.childs)):
            raise MapValidationError('Fields "name", "type", "template" and "child_type" must be List[Properties]'
                                     ' type with len < 2')
        for child in self.childs:
            child.validate()

@dataclass
class Objects:
    childs: List[Object]

    def validate(self):
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
    visible: Optional[bool]
    offsetx: Optional[float]
    offsety: Optional[float]
    draworder: Optional[str]
    properties: Properties
    objects: Objects
    childs: List[Union[Properties, Object]]

    def validate(self):
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
            return MapValidationError('Field "visible" must be None or False')
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



@dataclass
class Frame:
    tiled: int
    duration: int

    def validate(self):
        if not (isinstance(self.tiled, int) and isinstance(self.duration, int)):
            raise MapIntValidationError(('tiled', 'duration'))


@dataclass
class Animation:
    childs: List[Frame]

    def validate(self):
        if not (isinstance(self.childs, list) and all(isinstance(child, Frame) for child in self.childs)):
            raise MapValidationError('Field "childs" must be list of Frame')
        for child in self.childs:
            child.validate()


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

    def validate(self):
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


@dataclass
class WangColor:
    name: str
    color: Color
    tile: int
    probability: float

    def validation(self):
        if not isinstance(self.name, str):
            raise MapStrValidationError('name')
        if not isinstance(self.color, Color):
            raise MapValidationError('Field "color" must be Color')
        if not isinstance(self.tile, int):
            raise MapIntValidationError('tile')
        if not (self.probability is None or isinstance(self.probability, float) and self.probability > 0):
            raise MapFloatValidationError('probability', 0)


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


@dataclass
class WangSet:
    name: str
    tile: int
    wangcornercolors: List[WangColor]
    wangedgecolor: List[WangColor]
    wangtiles: List[WangTile]
    childs: List[Union[WangColor, WangTile]]

    def validate(self):
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


@dataclass
class TerrainTypes:
    childs: List[Terrain]

    def validate(self):
        if not (isinstance(self.childs, list) and all(isinstance(child, Terrain) for child in self.childs)):
            raise MapValidationError('Field "childs" must be list of Terrain')
        for child in self.childs:
            child.validate()


@dataclass
class Properties:
    childs: List[Property]

    def validate(self):
        if not (isinstance(self.childs, list) and len(self.childs) < 2 and all(isinstance(child, Property) for child in self.childs)):
            raise MapValidationError('Field "childs" must be list of Property')
        for child in self.childs:
            child.validate()


@dataclass
class WangSets:
    childs: List[WangSet]

    def validate(self):
        if not (isinstance(self.childs, list) and all(isinstance(child, WangSet) for child in self.childs)):
            raise MapValidationError('Field "childs" must be list of WangSet')


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

    def validate(self):
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


@dataclass
class Layer:
    id: int
    name: str
    x: Optional[int]
    y: Optional[int]
    width: int
    height: int
    opacity: Optional[float]
    visible: Optional[bool]
    offsetx: Optional[float]
    offsety: Optional[float]
    properties: Optional[Properties]
    data: Data  # validate Data len(tiles) if not infinite map?
    childs: List[Union[Properties, Data]]

    def validate(self):
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
        if self.visible:
            return MapValidationError('Field "visible" must be None or False')
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


@dataclass
class ImageLayer:
    id: int
    name: str
    offsetx: float
    offsety: float
    x: int
    y: int
    opacity: float
    visible: bool
    properties: Properties
    image: Image
    child: List[Union[Properties, Image]]

    def validate(self):
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
        if self.visible:
            return MapValidationError('Field "visible" must be None or False')
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


@dataclass
class Group:
    id: int
    name: str
    offsetx: float
    offsety: float
    opacity: float
    visible: bool
    properties: Properties
    layers: List[Layer]
    objectgroups: List[ObjectGroup]
    imagelayers: List[ImageLayer]
    groups: List[Group]
    childs: List[Properties, Layer, ObjectGroup, ImageLayer, Group]

    def validate(self):
        if not (isinstance(self.id, int) and self.id > 0):
            raise MapIntValidationError("id", 0)
        if not isinstance(self.name, str):
            raise MapValidationError('Field "name" must be str')
        if not all(field is None or isinstance(field, float) for field in (self.opacity, self.offsetx, self.offsety)):
            raise MapFloatValidationError(('opacity', 'offsetx', 'offsety'), none=True)
        if not (self.offsety is None and self.offsety is None or self.offsety is not None and self.offsety is not None):
            raise MapValidationError('Fields "offsetx" and "offsety" must be None or float together')
        if self.visible:
            return MapValidationError('Field "visible" must be None or False')
        if not (self.layers is None or isinstance(self.layers, Layer)):
            raise MapValidationError('Field "layers" must be None or Layer type')
        if not (self.objectgroups is None or isinstance(self.objectgroups, ObjectGroup)):
            raise MapValidationError('Field "objectgroups" must be None or ObjectGroup type')
        if not (self.imagelayers is None or isinstance(self.imagelayers, ImageLayer)):
            raise MapValidationError('Field "imagelayers" must be None or ImageLayer type')
        if not (self.groups is None or isinstance(self.groups, Group)):
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


class MapValidationError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message

    def __str__(self) -> str:
        return self.message


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
