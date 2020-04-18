from setuptools import setup, find_packages
setup(
    name="Cyclic Generated TMX",
    license='MIT',
    description='Read, change, write, generate, create animated images TMX maps.',
    long_description='Read, change, write, generate, create animated images TMX maps.',
    author='yobagram',
    url='https://github.com/yobagram/cyclic-gen-tmx',
    download_url='https://github.com/yobagram/cyclic-gen-tmx/archive/v_01.tar.gz',
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=["Pillow>=7.0.0"],
    keywords=['tmx', 'map', 'generation', 'save', 'image'],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
)
