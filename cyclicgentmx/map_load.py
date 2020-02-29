from __future__ import annotations
import pathlib
import xml.etree.ElementTree as ET
from cyclicgentmx.tmx_types import TileSet, ObjectGroup, Layer, ImageLayer, Group, Properties
from cyclicgentmx.helpers import int_or_none


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
        self.infinite = bool(int(root.attrib.get("infinite")))

        for child in root:
            if child.tag == 'properties':
                child_object = Properties.from_element(child)
                self.properties = child_object
            elif child.tag == 'tileset':
                child_object = TileSet.from_element(child, self.file_dir)
                self.tilesets.append(child_object)
            elif child.tag == 'layer':
                child_object = Layer.from_element(child)
                self.layers.append(child_object)
            elif child.tag == 'objectgroup':
                child_object = ObjectGroup.from_element(child)
                self.objectgroups.append(child_object)
            elif child.tag == 'imagelayer':
                child_object = ImageLayer.from_element(child)
                self.imagelayers.append(child_object)
            elif child.tag == 'group':
                child_object = Group.from_element(child)
                self.groups.append(child_object)
            else:
                continue
            self.childs.append(child_object)
        return self
