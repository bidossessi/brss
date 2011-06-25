from setuptools import setup, find_packages
import os, sys, glob, platform
from brss import __version__

data_files = []
if platform.system() in ('Linux', 'SunOS'):
    applications = glob.glob("brss/applications/*")
    icons = glob.glob("brss/icons/*")
    pixmaps = glob.glob("brss/pixmaps/*")
    data_files.extend([
        ("applications", applications),
        ("icons", icons),
        ("pixmaps", pixmaps),
        ])

setup(
    name='brss',
    packages = find_packages(),
    version = __version__,
    description = "Offline DBus RSS reader",
    fullname = "BRss Offline RSS Reader",
    long_description = open('README.txt').read(),
    classifiers = [
        "Programming Language :: Python",
        "Topic :: Internet",
        "Environment :: GTK ",
        "Intended Audience :: End Users/Desktop",
        "Operating System :: POSIX",
        ],
    author='Bidossessi SODONON',
    author_email='bidossessi.sodonon@yahoo.fr',
    zip_safe=False,

    entry_points = {
        'gui_scripts': [
            'brss-reader = brss:run_frontend',
            'brss-engine = brss:run_engine',
            ],
       },
    package_dir = {'client': 'coriolis/client'},
    package_data = {},
    include_package_data = True,
    data_files = data_files
)
