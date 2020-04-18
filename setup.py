from setuptools import setup, find_packages
setup(
    name="CyclicGeneratedTMX",
    packages=find_packages(),
    license='MIT',
    description='Read, change, write, generate, create animated images TMX maps.',
    long_description='Read, change, write, generate, create animated images TMX maps.',
    author='yobagram',
    url='https://github.com/yobagram/cyclic-gen-tmx',
    download_url='https://github.com/yobagram/cyclic-gen-tmx/archive/v_013.tar.gz',
    version="0.1.3",
    include_package_data=True,
    install_requires=["Pillow>=7.0.0"],
    keywords=['tmx', 'map', 'generation', 'save', 'image'],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: MIT License',
        "Programming Language :: Python :: 3",
    ],
    python_requires='>=3.7',
)
