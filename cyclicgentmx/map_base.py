from cyclicgentmx.map_load import MapLoad
from cyclicgentmx.map_valid import MapValid
from  cyclicgentmx.map_save import MapSave


class MapBase(MapLoad, MapValid, MapSave):
    pass