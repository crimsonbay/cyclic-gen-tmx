from __future__ import annotations
from typing import List
import base64
import gzip
import zlib
import pathlib
import xml.etree.ElementTree as ET
from cyclicgentmx.tmx_types import Color, Property, TileSet, TileOffset, Grid, Image, Data, Chunk, Terrain, \
    Tile, Object, Frame, ObjectGroup, Layer, ImageLayer, Group, WangSet, WangTile, WangColor, WangID, TerrainTypes, \
    Properties, WangSets, Animation, Objects
from cyclicgentmx.helpers import int_or_none, float_or_none, four_bytes


class MapLoad:
    @classmethod
    def from_file(cls, map_name: str) -> MapLoad:
        self = cls()
        self.file_dir = pathlib.PurePath(map_name).parent
        self.properties = None
        self.tilesets = []
        self.childs = []
        self.layers = []
        self.objectgroups = []
        self.imagelayers = []
        self.groups = []

        tree = ET.parse(map_name)
        root = tree.getroot()

        self.version = root.attrib.get("version", None)
        self.tiledversion = root.attrib.get("tiledversion", None)
        self.compressionlevel = int_or_none(root.attrib.get("compressionlevel", None))
        self.orientation = root.attrib.get("orientation")
        self.renderorder = root.attrib.get("renderorder")
        self.width = int(root.attrib.get("width"))
        self.height = int(root.attrib.get("height"))
        self.tilewidth = int(root.attrib.get("tilewidth"))
        self.tileheight = int(root.attrib.get("tileheight"))
        self.hexsidelength = int_or_none(root.attrib.get("hexsidelength", None))
        self.staggeraxis = root.attrib.get("staggeraxis", None)
        self.staggerindex = root.attrib.get("staggerindex", None)
        self.backgroundcolor = root.attrib.get("backgroundcolor", None)
        self.nextlayerid = int_or_none(root.attrib.get("nextlayerid", None))
        self.nextobjectid = int_or_none(root.attrib.get("nextobjectid", None))
        self.infinite = True if root.attrib.get("infinite", None) else False

        for child in root:
            if child.tag == 'properties':
                child_object = self.fill_properties(child)
                self.properties = child_object
            elif child.tag == 'tileset':
                child_object = self.create_tileset(child)
                self.tilesets.append(child_object)
            elif child.tag == 'layer':
                child_object = self.create_layer(child)
                self.layers.append(child_object)
            elif child.tag == 'objectgroup':
                child_object = self.create_objectgroup(child)
                self.objectgroups.append(child_object)
            elif child.tag == 'imagelayer':
                child_object = self.create_imagelayer(child)
                self.imagelayers.append(child_object)
            elif child.tag == 'group':
                child_object = self.create_group(child)
                self.groups.append(child_object)
            else:
                continue
            self.childs.append(child_object)
        return self

    def fill_properties(self, properties: ET.Element) -> Properties:
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
                value = pathlib.PurePath(self.file_dir, value).as_posix()
            else:
                continue
            result.append(Property(prop.attrib.get('name'),
                                   prop_type,
                                   value
                                   )
                          )
        return Properties(result)

    def create_tileset(self, tileset: ET.Element) -> TileSet:
        firstgid = int(tileset.attrib.get('firstgid'))
        source = tileset.attrib.get('source', None)
        if source:
            source_with_path = pathlib.PurePath(self.file_dir, source).as_posix()
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
                child_object = self.fill_properties(child)
                properties = child_object
            elif child.tag == 'image':
                child_object = self.create_image(child)
                image = child_object
            elif child.tag == 'terraintypes':
                child_object = self.fill_terraintypes(child)
                terraintypes = child_object
            elif child.tag == 'tile':
                child_object = self.create_tile(child)
                tiles.append(child_object)
            elif child.tag == 'wangsets':
                child_object = self.fill_wangsets(child)
                wangsets = child_object
            else:
                continue
            childs.append(child_object)

        return TileSet(firstgid, source, name, tilewidth, tileheight, spacing, margin, tilecount, columns,
                       version, tiledversion, tileoffset, grid, properties, image, terraintypes,
                       tiles, wangsets, childs)

    def create_image(self, image: ET.Element) -> Image:
        image_format = image.attrib.get('format')
        source = image.attrib.get('source')
        trans = Color(image.attrib.get('trans')) if image.attrib.get('trans', None) else None
        width = int_or_none(image.attrib.get('width'))
        height = int_or_none(image.attrib.get('height'))
        data = None
        childs = []

        for child in image:
            if child.tag == 'data':
                data = self.create_data(child)
                childs.append(data)
        return Image(image_format, source, trans, width, height, data, childs)

    def fill_tiles(self, data: ET.Element, encoding: str, compression: str) -> List[int]:
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

    def create_data(self, data: ET.Element) -> Data:
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
                child_tiles = self.fill_tiles(child, encoding, compression)
                child_object = Chunk(x, y, width, height, child_tiles)
                chunks.append(child_object)
            childs = chunks
        else:
            tiles = self.fill_tiles(data, encoding, compression)
            childs = tiles
        return Data(encoding, compression, tiles, chunks, childs)

    def fill_terraintypes(self, terraintypes: ET.Element) -> TerrainTypes:
        result = []
        for terrain in terraintypes:
            if terrain.tag == 'terrain':
                name = terrain.attrib.get("name")
                tile = terrain.attrib.get("tile")
                properties = None
                childs = []
                for terrain_properties in terrain:
                    if terrain_properties.tag == 'properties':
                        properties = self.fill_properties(terrain_properties)
                        childs.append(properties)
                    else:
                        continue
                result.append(Terrain(name, tile, properties, childs))
        return TerrainTypes(result)

    def create_tile(self, tile: ET.Element) -> Tile:
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
                child_object = self.fill_properties(child)
                properties = child_object
            elif child.tag == 'image':
                child_object = self.create_image(child)
                image = child_object
            elif child.tag == 'objectgroup':
                child_object = self.create_objectgroup(child)
                objectgroup = child_object
            elif child.tag == 'animation':
                child_object = self.fill_animation(child)
                animation = child_object
            else:
                continue
            childs.append(child_object)
        return Tile(tile_id, tile_type, terrain, probability, properties, image, objectgroup, animation, childs)

    def fill_animation(self, animation: ET.Element) -> Animation:
        result = []
        for frame in animation:
            if frame.tag == 'frame':
                tileid = int(frame.attrib.get('tileid'))
                duration = int(frame.attrib.get('tileid'))
                result.append(Frame(tileid, duration))
        return Animation(result)

    def create_objectgroup(self, objectgroup: ET.Element) -> ObjectGroup:
        objectgroup_id = int(objectgroup.attrib.get('id'))
        name = objectgroup.attrib.get('name')
        color = Color(objectgroup.attrib.get('color', None)) if objectgroup.attrib.get('color', None) else None
        x = int_or_none(objectgroup.attrib.get('x', None))
        y = int_or_none(objectgroup.attrib.get('y', None))
        width = int_or_none(objectgroup.attrib.get('width', None))
        height = int_or_none(objectgroup.attrib.get('height', None))
        opacity = float_or_none(objectgroup.attrib.get('opacity', None))
        visible = True if objectgroup.attrib.get('visible', True) else False
        offsetx = float_or_none(objectgroup.attrib.get('offsetx', None))
        offsety = float_or_none(objectgroup.attrib.get('offsety', None))
        draworder = objectgroup.attrib.get('draworder', None)

        properties = None
        objects = []
        childs = []

        for child in objectgroup:
            if child.tag == 'properties':
                properties = self.fill_properties(child)
                childs.append(properties)
            elif child.tag == 'object':
                child_object = self.create_object(child)
                objects.append(child_object)
                childs.append(child_object)
        return ObjectGroup(objectgroup_id, name, color, x, y, width, height, opacity, visible,
                           offsetx, offsety, draworder, properties, Objects(objects), childs)

    def create_object(self, object: ET.Element) -> Object:
        object_id = object.attrib.get('id')
        name = object.attrib.get('id', None)
        object_type = object.attrib.get('id', None)
        x = object.attrib.get('x')
        y = object.attrib.get('y')
        width = float_or_none(object.attrib.get('width', None))
        height = float_or_none(object.attrib.get('height', None))
        rotation = float_or_none(object.attrib.get('rotation', None))
        gid = int_or_none(object.attrib.get('gid', None))
        visible = False if object.attrib.get('visible', '1') else None
        template = object.attrib.get('template', None)
        child_type = None
        properties = None
        childs = []
        for child in object:
            if child.tag == 'properties':
                properties = self.fill_properties(child)
                childs.append(properties)
            else:
                child_type = child.tag
        return Object(object_id, name, object_type, x, y, width, height, rotation, gid, visible, template, child_type,
                      properties, childs)

    def create_layer(self, layer: ET.Element) -> Layer:
        layer_id = int_or_none(layer.attrib.get('id', None))
        name = layer.attrib.get('name', None)
        x = int_or_none(layer.attrib.get('x', None))
        y = int_or_none(layer.attrib.get('y', None))
        width = int_or_none(layer.attrib.get('width', None))
        height = int_or_none(layer.attrib.get('height', None))
        opacity = float_or_none(layer.attrib.get('opacity', None))
        visible = True if layer.attrib.get('visible', True) else False
        offsetx = float_or_none(layer.attrib.get('offsetx', None))
        offsety = float_or_none(layer.attrib.get('offsety', None))

        properties = None
        data = None
        childs = []

        for child in layer:
            if child.tag == 'properties':
                properties = self.fill_properties(child)
                childs.append(properties)
            elif child.tag == 'data':
                data = self.create_data(child)
                childs.append(data)
        return Layer(layer_id, name, x, y, width, height, opacity, visible,
                     offsetx, offsety, properties, data, childs)

    def create_imagelayer(self, layer: ET.Element) -> ImageLayer:
        imagelayer_id = int_or_none(layer.attrib.get('id', None))
        name = layer.attrib.get('name', None)
        offsetx = float_or_none(layer.attrib.get('offsetx', None))
        offsety = float_or_none(layer.attrib.get('offsety', None))
        x = int_or_none(layer.attrib.get('x', None))
        y = int_or_none(layer.attrib.get('y', None))
        opacity = float_or_none(layer.attrib.get('opacity', None))
        visible = True if layer.attrib.get('visible', True) else False

        properties = None
        image = None
        childs = []

        for child in layer:
            if child.tag == 'properties':
                properties = self.fill_properties(child)
                childs.append(properties)
            elif child.tag == 'image':
                image = self.create_image(child)
                childs.append(image)
        return ImageLayer(imagelayer_id, name, offsetx, offsety, x, y, opacity, visible, properties, image, childs)

    def create_group(self, group: ET.Element) -> Group:
        group_id = int_or_none(group.attrib.get('id', None))
        name = group.attrib.get('name', None)
        offsetx = float_or_none(group.attrib.get('offsetx', None))
        offsety = float_or_none(group.attrib.get('offsety', None))
        opacity = float_or_none(group.attrib.get('opacity', None))
        visible = True if group.attrib.get('visible', True) else False

        properties = None
        group_layers = []
        layers = []
        objectgroups = []
        imagelayers = []
        groups = []
        childs = []

        for child in group:
            if child.tag == 'properties':
                child_object = self.fill_properties(child)
                properties = child_object
            elif child.tag == 'layer':
                child_object = self.create_layer(child)
                layers.append(child_object)
                group_layers.append(child_object)
            elif child.tag == 'objectgroup':
                child_object = self.create_objectgroup(child)
                objectgroups.append(child_object)
                group_layers.append(child_object)
            elif child.tag == 'imagelayer':
                child_object = self.create_imagelayer(child)
                imagelayers.append(child_object)
                group_layers.append(child_object)
            elif child.tag == 'group':
                child_object = self.create_group(child)
                groups.append(child_object)
                group_layers.append(child_object)
            else:
                continue
            childs.append(child_object)
        return Group(group_id, name, offsetx, offsety, opacity, visible, properties,
                     layers, objectgroups, imagelayers, groups, childs)

    def fill_wangsets(self, wangsets: ET.Element) -> WangSets:
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
                        child_tile = child.attrib.get('tile', None)
                        probability = float_or_none(child.attrib.get('probability', None))
                        wangcolor = WangColor(name, color, child_tile, probability)
                        wangcornercolors.append(wangcolor)
                        childs.append(wangcolor)
                    elif child.tag == 'wangedgecolor':
                        name = child.attrib.get('name', None)
                        color = Color(child.attrib.get('color', None)) if child.attrib.get('color', None) else None
                        child_tile = child.attrib.get('tile', None)
                        probability = float_or_none(child.attrib.get('probability', None))
                        wangcolor = WangColor(name, color, child_tile, probability)
                        wangedgecolor.append(wangcolor)
                        childs.append(wangcolor)
                    elif child.tag == 'wangtile':
                        tileid = wangset.attrib.get('tileid', None)
                        wangid = wangset.attrib.get('wangid', None)
                        if wangid:
                            wangid = WangID(wangid)
                        wangtile = WangTile(tileid, wangid)
                        wangtiles.append(wangtile)
                        childs.append(wangtile)
                result.append(WangSet(name, tile, wangcornercolors, wangedgecolor, wangtiles, childs))
        return WangSets(result)
