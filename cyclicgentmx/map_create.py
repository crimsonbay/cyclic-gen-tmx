from __future__ import annotations
import pathlib
from cyclicgentmx.tmx_types import Layer, Data, Color


class MapCreate:

    @classmethod
    def create_empty(cls, orientation: str, width: int, height: int, tilewidth: int, tileheight: int,
                     version: str = '1.2', tiledversion: str = '1.3.1', compressionlevel: int = -1,
                     renderorder: str = 'right-down', hexsidelength: int = None, staggeraxis: int = None,
                     staggerindex: int = None, backgroundcolor: str = None, infinite: bool = False,
                     map_name: str = None
                     ) -> MapCreate:
        self = cls()
        if map_name and isinstance(map_name.str):
            self.file_dir = pathlib.PurePath(map_name).parent
        else:
            self.file_dir = pathlib.PurePosixPath()
        self.properties = None
        self.tilesets = []
        self.childs = []
        self.layers = []
        self.objectgroups = []
        self.imagelayers = []
        self.groups = []

        self.version = version
        self.tiledversion = tiledversion
        self.compressionlevel = compressionlevel
        self.orientation = orientation
        self.renderorder = renderorder
        self.width = width
        self.height = height
        self.tilewidth = tilewidth
        self.tileheight = tileheight
        self.hexsidelength = hexsidelength
        self.staggeraxis = staggeraxis
        self.staggerindex = staggerindex
        self.backgroundcolor = Color(backgroundcolor) if backgroundcolor else None
        self.nextlayerid = 1
        self.nextobjectid = 1
        self.infinite = infinite

        chunks = []
        if not infinite:
            tiles = [0] * ((width - 1) * (height - 1))
            childs = tiles
        else:
            tiles = []
            childs = chunks
        data = Data(encoding="base64", compression="zlib", tiles=tiles, chunks=chunks, childs=childs)
        layer = Layer(id=1, name="Tile Layer 1", x=None, y=None, width=width, height=height,
                      opacity=None, visible=None, offsetx=None, offsety=None, properties=None, data=data, childs=childs)
        self.layers.append(layer)
        self.childs.append(data)
        return self
