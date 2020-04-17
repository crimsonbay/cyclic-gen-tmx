from cyclicgentmx.map_load import MapLoad
from cyclicgentmx.map_valid import MapValid
from cyclicgentmx.map_save import MapSave
from cyclicgentmx.map_image import MapImage


class MapBase(MapLoad, MapValid, MapSave, MapImage):
    pass