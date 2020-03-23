from __future__ import annotations
import pathlib
import xml.etree.ElementTree as ET
from cyclicgentmx.helpers import clear_dict_from_none, indent


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
        new_file_dir = pathlib.PurePath(map_name).parent
        root = ET.Element('map', attrib=clear_dict_from_none(attrib))
        for child in self.childs:
            root.append(child.get_element(self.file_dir, new_file_dir))

        indent(root)
        tree = ET.ElementTree(root)
        tree.write(map_name, encoding="UTF-8", xml_declaration=True)
