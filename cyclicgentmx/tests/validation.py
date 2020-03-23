from cyclicgentmx.map_base import MapBase
from cyclicgentmx.helpers import get_size
import pathlib


filenames = ('test_map', 'test_map_csv', 'test_map_base64', 'test_map_base64_gzip', 'test_map_base64_zlib', 'infinite')
for filename in filenames:
    test_map = pathlib.Path(__file__).parent.absolute().joinpath('data/{}.tmx'.format(filename)).as_posix()
    m = MapBase.from_file(test_map)
    m.validate()
    print(get_size(m))

print('Validation test OK')

for filename in filenames[:-1]:
    test_map = pathlib.Path(__file__).parent.absolute().joinpath('data/{}.tmx'.format(filename)).as_posix()
    m = MapBase.from_file(test_map)
    m.save('xxx.tmx')
    m.create_base_map_image()  # temporarily here

print('Save test OK')
