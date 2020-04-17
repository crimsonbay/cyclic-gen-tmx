from setuptools import setup, find_packages
setup(
    name="Cyclic Generated TMX",
    license='MIT',
    description='Read, change, write, generate, create animated images TMX maps.',
    author='yobagram',
    url='https://github.com/yobagram/cyclic-gen-tmx',
    download_url='https://github.com/yobagram/cyclic-gen-tmx/archive/v_01.tar.gz',
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=["Pillow>=7.0.0"],
    keywords=['tmx', 'map', 'generation', 'save', 'image'],
)
