from __future__ import annotations
from typing import List, Optional
import os
from PIL import Image
from cyclicgentmx.tmx_types import MapError
from collections import defaultdict

from cyclicgentmx.helpers import lcm


class MapImage:
    def _generate_lazy_tileset_images(self) -> List[Image]:
        result = [None, ]
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
        self._lazy_tileset_images = result

    def _generate_animation_substitutions(self, max_frames: int = 50) -> dict:
        animation_substitutions = defaultdict(dict)
        all_animated_tile_gids = set()
        tiles_frames = list()
        durations = list()
        for tileset in self.tilesets:
            for tile in tileset.tiles:
                if tile.animation:
                    tile_id = tile.id + tileset.firstgid
                    used_tile = any(tile_id in layer.data.tiles for layer in self.layers)
                    if used_tile:
                        duration_before = 0
                        all_animated_tile_gids.add(tile_id)
                        tile_animation_substitutions = defaultdict(dict)
                        for frame in tile.animation.childs:
                            time_element = tile_animation_substitutions[duration_before]
                            time_element[tile_id] = frame.tileid + tileset.firstgid
                            duration_before += frame.duration
                        durations.append(duration_before)
                        tile_frame = {'duration': duration_before, 'substitutions': tile_animation_substitutions}
                        tiles_frames.append(tile_frame)
        if not durations:
            self._animation_substitutions = animation_substitutions
            self._all_animated_tile_gids = all_animated_tile_gids
            return
        lcm_time = lcm(durations)
        for tile_frame in tiles_frames:
            frame_duration = tile_frame['duration']
            substitutions = tile_frame['substitutions']
            time_shift = 0
            for i in range(lcm_time // frame_duration):
                for time in substitutions:
                    animation_substitutions[time + time_shift].update(substitutions[time])
                time_shift += frame_duration
        self._animation_substitutions = animation_substitutions
        self._all_animated_tile_gids = all_animated_tile_gids
        self._animation_time = lcm_time
        frames_count = len(self._animation_substitutions)
        if frames_count > max_frames:
            raise MapError('Map has more frames({}) then max_frames({})'.format(frames_count, max_frames))

    def _create_map_image_frame(self, substitution: Optional[dict] = None, previous_image: Optional[Image] = None,
                                only_update: bool = False) -> Image:

        if self.orientation == 'orthogonal':
            return self._create_orthogonal_map_image_frame(substitution, previous_image, only_update)

        elif self.orientation == 'isometric':
            return self._create_isometric_map_image_frame(substitution, previous_image, only_update)

        elif self.orientation in ('staggered', 'hexagonal'):
            return self._create_staggered_map_image_frame(substitution, previous_image, only_update)

    def _create_orthogonal_map_image_frame(self, substitution: Optional[dict] = None,
                                           previous_image: Optional[Image] = None,
                                           only_update: bool = False
                                           ) -> Image:
        if self.infinite:
            raise MapError('Can not create image of infinite map.')
        tilewidth = self.tilewidth
        tileheight = self.tileheight
        if not previous_image:
            result_image = Image.new('RGBA', (self.width*tilewidth, self.height*tileheight))
        else:
            result_image = previous_image.copy()
        if not substitution:
            substitution = dict()
        substitute = bool(substitution)
        was_changed = False
        for layer in self.layers:
            height_range = range(layer.height)
            width_range = range(layer.width)
            if self.renderorder == 'right-up':
                height_range = reversed(height_range)
            elif self.renderorder == 'left-down':
                width_range = reversed(width_range)
            elif self.renderorder == 'left-up':
                width_range = reversed(width_range)
                height_range = reversed(height_range)
            layer_image = Image.new('RGBA', (layer.width*tilewidth, layer.height*tileheight))
            width_range = list(width_range)
            height_range = list(height_range)
            for j in height_range:
                j_compont = j * layer.height
                for i in width_range:
                    tile_id = j_compont + i
                    gid = layer.data.tiles[tile_id]
                    old_gid = gid
                    if substitute and only_update:
                        gid = substitution.get(gid)
                    else:
                        gid = substitution.get(gid, gid)
                    if old_gid != gid:
                        was_changed = True
                    if gid:
                        image = self._lazy_tileset_images[gid]
                        delta_height = image.size[0] - tileheight
                        layer_image.paste(image, (i*tilewidth, j*tileheight - delta_height), image.convert('RGBA'))
            result_image = Image.alpha_composite(result_image, layer_image)
        return result_image, was_changed

    def _create_isometric_map_image_frame(self, substitution: Optional[dict] = None,
                                          previous_image: Optional[Image] = None,
                                          only_update: bool = False
                                          ) -> Image:
        if self.infinite:
            raise MapError('Can not create image of infinite map.')
        tilewidth = self.tilewidth
        tileheight = self.tileheight
        x_size = (self.width + self.height) * tilewidth // 2
        y_size = (self.width + self.height) * tileheight // 2
        if not previous_image:
            result_image = Image.new('RGBA', (x_size, y_size))
        else:
            result_image = previous_image.copy()
        if not substitution:
            substitution = dict()
        substitute = bool(substitution)
        was_changed = False
        for layer in self.layers:
            tile_id = 0
            layer_image = Image.new('RGBA', (x_size, y_size))
            for j in range(layer.height):
                for i in range(layer.width):
                    gid = layer.data.tiles[tile_id]
                    old_gid = gid
                    if substitute and only_update:
                        gid = substitution.get(gid)
                    else:
                        gid = substitution.get(gid, gid)
                    if old_gid != gid:
                        was_changed = True
                    if gid:
                        image = self._lazy_tileset_images[gid]
                        layer_image.paste(image,
                                          ((i - j + layer.height - 1) * tilewidth // 2,
                                           (j + i - 2) * tileheight // 2), image.convert('RGBA')
                                          )
                    tile_id += 1
            result_image = Image.alpha_composite(result_image, layer_image)
        return result_image, was_changed

    def _create_staggered_map_image_frame(self, substitution: Optional[dict] = None,
                                          previous_image: Optional[Image] = None,
                                          only_update: bool = False
                                          ) -> Image:
        if self.infinite:
            raise MapError('Can not create image of infinite map.')
        tilewidth = self.tilewidth
        tileheight = self.tileheight
        hexsidelength = self.hexsidelength if self.hexsidelength else 0
        if self.staggeraxis == 'y':
            x_size = self.width * tilewidth + tilewidth // 2
            y_size = (self.height + 1) * (tileheight + hexsidelength) // 2 - hexsidelength
        else:
            x_size = ((self.width + 1) * (tilewidth + hexsidelength)) // 2 - hexsidelength
            y_size = self.height * tileheight + tileheight // 2
        if not previous_image:
            result_image = Image.new('RGBA', (x_size, y_size))
        else:
            result_image = previous_image.copy()
        if not substitution:
            substitution = dict()
        substitute = bool(substitution)
        was_changed = False
        if self.staggerindex == 'even':
            even = 1
            i_range = list(range(1, self.width, 2))
            i_range.extend(list(range(0, self.width, 2)))
        else:
            even = 0
            i_range = list(range(0, self.width, 2))
            i_range.extend(list(range(1, self.width, 2)))
        for layer in self.layers:
            layer_image = Image.new('RGBA', (x_size, y_size))
            for j in range(layer.height):
                j_width = j * self.width
                for i in i_range:
                    tile_id = j_width + i
                    gid = layer.data.tiles[tile_id]
                    old_gid = gid
                    if substitute and only_update:
                        gid = substitution.get(gid)
                    else:
                        gid = substitution.get(gid, gid)
                    if old_gid != gid:
                        was_changed = True
                    if gid:
                        image = self._lazy_tileset_images[gid]
                        if self.staggeraxis == 'y':
                            layer_image.paste(image,
                                              (i * tilewidth + ((j + even) % 2) * tilewidth // 2,
                                               (j - 2) * (tileheight + hexsidelength) // 2 + hexsidelength),
                                              image.convert('RGBA')
                                              )
                        else:
                            layer_image.paste(image,
                                              (i * (tilewidth + hexsidelength) // 2,
                                               (j - 1) * tileheight + ((i + even) % 2) * tileheight // 2),
                                              image.convert('RGBA')
                                              )
            result_image = Image.alpha_composite(result_image, layer_image)
        return result_image, was_changed

    def create_animated_image(self, name: str) -> Image:
        self._generate_lazy_tileset_images()
        self._generate_animation_substitutions()
        if not self._animation_substitutions:
            return self._create_map_image_frame()
        frames = list()
        prev_frame = None
        duration = list()
        prev_time = None
        only_update = False
        for substitution_time in sorted(self._animation_substitutions.keys()):
            frame, was_changed = self._create_map_image_frame(self._animation_substitutions[substitution_time],
                                                              prev_frame,
                                                              only_update)
            only_update = True
            if not prev_frame or was_changed:
                frames.append(frame)
                if prev_time is not None:
                    duration.append(substitution_time - prev_time)
                    prev_time = substitution_time
                else:
                    prev_time = 0
                prev_frame = frame
        duration.append(self._animation_time - prev_time)
        result_gif = Image.new('RGBA', (self.width*self.tilewidth, self.height*self.tileheight))
        result_gif.paste(frames[0])
        result_gif.save(name, 'GIF', save_all=True, append_images=frames[1:],
                        duration=duration, loop=0, transparency=255, disposal=2)
