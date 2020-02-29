from __future__ import annotations
from typing import List
import base64
import gzip
import zlib
import itertools
import pathlib
import xml.etree.ElementTree as ET
from cyclicgentmx.map_valid import MapValid
from cyclicgentmx.tmx_types import Layer, Data, MapValidationError, MapIntValidationError, Color, Properties, TileSet,\
    ObjectGroup, ImageLayer, Group
from cyclicgentmx.helpers import clear_dict_from_none


class MapSave:

    def save(self, map_name: str) -> None:
        attrib = {
            'version': self.version,
            'tiledversion': self.tiledversion,
            'compressionlevel': self.compressionlevel,
            'orientation': self.orientation,
            'renderorder': self.renderorder,
            'width': self.width,
            'height': self.height,
            'tilewidth': self.tilewidth,
            'tileheight': self.tileheight,
            'hexsidelength': self.hexsidelength,
            'staggeraxis': self.staggeraxis,
            'staggerindex': self.staggerindex,
            'backgroundcolor': self.backgroundcolor,
            'nextlayerid': self.nextlayerid,
            'nextobjectid': self.nextobjectid,
            'infinite': '1' if self.infinite else '0'
        }
        root = ET.Element("map", attrib=clear_dict_from_none(attrib))
        tree = ET.ElementTree(root)
        tree.write(map_name, encoding="UTF-8", xml_declaration=True)