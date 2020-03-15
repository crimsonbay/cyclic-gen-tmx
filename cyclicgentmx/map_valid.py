from __future__ import annotations
import itertools
import pathlib
from cyclicgentmx.tmx_types import Layer, MapValidationError, MapIntValidationError, Properties, TileSet, \
    ObjectGroup, ImageLayer, Group


class MapValid:

    MAP_MANDATORY_FIELDS = frozenset(('orientation', 'width', 'height', 'tilewidth', 'tileheight', 'version',
                                      'tiledversion', 'compressionlevel', 'renderorder', 'nextlayerid', 'nextobjectid'))
    HEXAGONAL_MANDATORY_FIELDS = frozenset(('hexsidelength', 'staggeraxis', 'staggerindex'))

    def validate(self):
        all_fields = self.__dict__.keys()
        missing_fields = self.MAP_MANDATORY_FIELDS.difference(all_fields)
        if missing_fields:
            raise MapValidationError('Missing mandatory fields: {}'.format(missing_fields))
        not_defined_mandatory_fields = [field for field in self.MAP_MANDATORY_FIELDS if self.__dict__[field] is None]
        if not_defined_mandatory_fields:
            raise MapValidationError('Some mandatory fields is None: {}'.format(missing_fields))

        if self.orientation not in ('orthogonal', 'isometric', 'staggered', 'hexagonal'):
            raise MapValidationError('Field "orientation" must be in '
                                     '("orthogonal", "isometric", "staggered", "hexagonal")')

        if not all(isinstance(item, int) and item > 0
                   for item in (self.width, self.height, self.tilewidth, self.tileheight,
                                self.nextlayerid, self.nextobjectid)):
            raise MapIntValidationError(('width', 'height', 'tilewidth', 'tileheight',
                                         'nextlayerid', 'nextobjectid'), 0)

        if not (isinstance(self.compressionlevel, int) and -2 < self.compressionlevel < 10):
            raise MapIntValidationError('compressionlevel', -2, 10)

        if self.renderorder not in ('right-down', 'right-up', 'left-down', 'left-up'):
            raise MapValidationError('Field "compressionlevel" must be in '
                                     '("right-down", "right-up", "left-down", "left-up")')

        missing_fields = self.HEXAGONAL_MANDATORY_FIELDS.difference(all_fields)
        if missing_fields:
            raise MapValidationError('Missing hexagonal map mandatory fields: {}'.format(missing_fields))

        if self.orientation == 'hexagonal':
            not_defined_mandatory_fields = [field for field in self.HEXAGONAL_MANDATORY_FIELDS if
                                            self.__dict__[field] is None]
            if not_defined_mandatory_fields:
                raise MapValidationError('Some hexagonal map mandatory fields is None: {}'.format(missing_fields))

            if not (isinstance(self.hexsidelength, int) and self.hexsidelength > -1):
                raise MapIntValidationError('hexsidelength', -1)

            if self.staggeraxis not in ['x', 'y']:
                raise MapValidationError('Field "compressionlevel" must be in ("x", "y")')

            if self.staggerindex not in ['odd', 'even']:
                raise MapValidationError('Field "compressionlevel" must be in ("odd", "even")')
        else:
            defined_mandatory_fields = [field for field in self.HEXAGONAL_MANDATORY_FIELDS if
                                            self.__dict__[field] is not None]
            if defined_mandatory_fields:
                raise MapValidationError('Some not hexagonal map mandatory fields '
                                         'is not None: {}'.format(missing_fields))

        if not isinstance(self.infinite, bool):
            raise MapValidationError('Field "infinite" must be bool')
        if not (hasattr(self, 'file_dir') and isinstance(self.file_dir, pathlib.PurePath)):
            raise MapValidationError('Field "file_dir" must be pathlib.PurePath path')

        if not (self.properties is None or isinstance(self.properties, Properties)):
            raise MapValidationError('Field "file_dir" must be None or Properties type')
        elif self.properties is not None:
            self.properties.validate()
        for tileset in self.tilesets:
            if not isinstance(tileset, TileSet):
                raise MapValidationError('tileset in tilesets must be TileSet type')
            tileset.validate()
        for layer in self.layers:
            if not isinstance(layer, Layer):
                raise MapValidationError('layer in layers must be Layer type')
            layer.validate()
        for objectgroup in self.objectgroups:
            if not isinstance(objectgroup, ObjectGroup):
                raise MapValidationError('objectgroup in objectgroups must be ObjectGroup type')
            objectgroup.validate()
        for imagelayer in self.imagelayers:
            if not isinstance(imagelayer, ImageLayer):
                raise MapValidationError('imagelayer in imagelayers must be ImageLayer type')
            imagelayer.validate()
        for group in self.groups:
            if not isinstance(group, Group):
                raise MapValidationError('group in groups must be Group type')
            group.validate()
        childs_from_lists = list(itertools.chain(self.tilesets, self.layers, self.objectgroups,
                                                 self.imagelayers, self.groups))
        childs_from_lists.append(self.properties)
        if not all(item in self.childs for item in childs_from_lists)\
                and not all(item in childs_from_lists for item in self.childs):
            raise MapValidationError('items in "childs" not equal all items in "properties", "tilesets", "layers",'
                                     '"objectgroups", "imagelayers" and "groups"')
