"""Installation and deployment script."""
from setuptools import find_packages, setup


description = 'NFC enabled logger for beer drinking log.'

long_description = (
    'BeerLog is a tool to help alcoholics keep track of their beer intake.\n'
    'It currently supports displaying a scoreboard on a OLED device on a'
    'RaspberryPi, with a NFC scanner to help detect who is reporting their '
    'drinks.')

setup(
    name='beerlog',
    version='20190625',
    description=description,
    long_description=long_description,
    url='https://github.com/conchyliculture/beerlog',
    author='beerlog development team',
    license='MIT License',
    packages=find_packages(exclude=['beerlog.cli']),
    classifiers=[
        'Development Status :: 4 - Beta',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
    ],
    entry_points={
        'console_scripts': ['beerlog=beerlog.cli.beerlog_cli:Main']
    },
)
