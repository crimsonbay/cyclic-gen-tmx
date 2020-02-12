from __future__ import annotations
from typing import Any, List, Union
from dataclasses import dataclass


class Color:
    def __init__(self, hex_color: str) -> None:
        self.hex_color = hex_color

    @property
    def hex_color(self) -> str:
        return '#' + self.without_sharp_hex_color()

    @property
    def without_sharp_hex_color(self) -> str:
        if self.a:
            colors = (self.a, self.r, self.g, self.b)
        else:
            (self.r, self.g, self.b)
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


@dataclass
class TileOffset:
    x: int
    y: int


@dataclass
class Grid:
    orientation: str
    width: int
    height: int


@dataclass
class Chunk:
    x: int
    y: int
    width: int
    height: int
    tiles: List[int]


@dataclass
class Data:
    encoding: str
    compression: str
    tiles: List[int]
    chunks: List[Chunk]
    childs: Union[List[int], List[Chunk]]


@dataclass
class Image:
    format: str
    source: str
    trans: Color
    width: int
    height: int
    data: Data
    childs: List[Data]


@dataclass
class Terrain:
    name: str
    tile: str
    properties: Properties


@dataclass
class Object:
    id: int
    name: str
    type: str
    x: float
    y: float
    width: float
    height: float
    rotation: float
    gid: int
    visible: bool
    template: str
    child_type: str


@dataclass
class Objects:
    childs: List[Object]


@dataclass
class ObjectGroup:
    id: int
    name: str
    color: Color
    x: int
    y: int
    width: int
    height: int
    opacity: float
    visible: bool
    offsetx: float
    offsety: float
    draworder: str
    properties: Properties
    objects: Objects
    childs: List[Properties, Object]


@dataclass
class Frame:
    tiled: int
    duration: int


@dataclass
class Animation:
    childs: List[Frame]


@dataclass
class Tile:
    id: int
    type: str
    terrain: List[int]
    probability: float
    properties: Properties
    image: Image
    objectgroup: ObjectGroup
    animation: Animation
    childs: List[Union[Properties, Image, ObjectGroup, Animation]]


@dataclass
class WangColor:
    name: str
    color: Color
    tile: int
    probability: float


class WangID:
    def __init__(self, idstr: str) -> None:
        self.up, self.up_right, self.right, self.down_right, self.down, self.down_left, self.left, self.up_left = \
            0, 0, 0, 0, 0, 0, 0, 0
        self.__ids = (self.up, self.up_right, self.right, self.down_right,
                      self.down, self.down_left, self.left, self.up_left)
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


@dataclass
class WangSet:
    name: str
    tile: int
    wangcornercolors: List[WangColor]
    wangedgecolor: List[WangColor]
    wangtiles: List[WangTile]
    childs: List[Union[WangColor, WangTile]]


@dataclass
class TerrainTypes:
    childs: List[Terrain]


@dataclass
class Properties:
    childs: List[Property]


@dataclass
class WangSets:
    childs: List[WangSet]


@dataclass
class TileSet:
    firstgid: int
    source: str
    name: str
    tilewidth: int
    tileheight: int
    spacing: int
    margin: int
    tilecount: int
    columns: int
    version: str
    tiledversion: str
    tileoffset: TileOffset
    grid: Grid
    properties: Properties
    image: Image
    terraintypes: TerrainTypes
    tiles: List[Tile]
    wangsets: WangSets
    childs: List[Union[TileOffset, Grid, Property, Image, TerrainTypes, Tile, WangSets]]


@dataclass
class Layer:
    id: int
    name: str
    x: int
    y: int
    width: int
    height: int
    opacity: float
    visible: bool
    offsetx: float
    offsety: float
    properties: Properties
    data: Data
    childs: List[Union[Properties, Data]]


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
