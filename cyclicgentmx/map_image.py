from __future__ import annotations
import os
from PIL import Image
from cyclicgentmx.tmx_types import MapValidationError


class MapImage:
    def _generate_lazy_tilset_images(self) -> Image:
        result = [None,]
        for tileset in self.tilesets:
            source = os.path.normpath(os.path.join(self.file_dir, tileset.image.source))
            tilset_image = Image.open(source)
            if tilset_image.mode != 'RGBA':
                tilset_image = tilset_image.convert(mode='RGBA', )
            margin = tileset.margin if tileset.margin else 0
            spacing = tileset.spacing if tileset.spacing else 0
            height = tileset.tileheight
            width = tileset.tilewidth
            i_shift = spacing + width
            j_shift = spacing + height
            for j in range(tileset.tilecount // tileset.columns):
                j_coord = margin + j_shift * j
                for i in range(tileset.columns):
                    result.append(tilset_image.crop((margin + i_shift * i, j_coord,
                                                    margin + i_shift * i + width, j_coord + height),))
        return result

    def create_base_map_image(self) -> Image:
        if self.infinite:
            raise MapValidationError('Can not create image of infinite map.')
        lazy_tileset_images = self._generate_lazy_tilset_images()
        tilewidth = self.tilewidth
        tileheight = self.tileheight
        result_image = Image.new('RGBA', (self.width*tilewidth, self.height*tileheight))
        for layer in self.layers:
            tile_id = 0
            for j in range(layer.height):
                for i in range(layer.width):
                    gid = layer.data.tiles[tile_id]
                    image = lazy_tileset_images[gid]
                    if gid:
                        delta_height = image.size[0] - tileheight
                        result_image.paste(image, (i*tilewidth, j*tileheight - delta_height))
                    tile_id += 1
        return result_image