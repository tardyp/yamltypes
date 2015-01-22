#!/usr/bin/env python
"""Installs cactus using setuptools

Run:
    python setup.py install
to install the package from the source archive.
"""
from setuptools import find_packages
from setuptools import setup
import os

version = 1.0
README = open(os.path.join(os.path.dirname(__file__), "README.rst")).read()

setup(
    name="yamlconfig",
    version=version,
    url="http://github.com/tardyp/yamlconfig",
    description="tools for validating, documenting, and editing json and yaml data",
    author="Pierre Tardy",
    author_email="tardyp@gmail.com",
    install_requires=[
        'Mock',
        'pyyaml',
        'dictns == 1.4',
        'nose >= 1.0 '

    ],
    license="BSD",
    packages=find_packages(),
    options={
        'sdist': {
            'force_manifest': 1,
            'formats': ['gztar', 'zip'], },
    },
    entry_points={
        'console_scripts': [
            'yamlconfig=yamlconfig.cli:main',
            'yaml2rst=yamlconfig.yaml2rst:main',
        ],
    },
    classifiers=[
        """License :: OSI Approved :: BSD License""",
        """Programming Language :: Python""",
        """Topic :: Software Development :: Libraries :: Python Modules""",
        """Intended Audience :: Developers""",
    ],
    keywords='yaml,schema',
    long_description=README,
    platforms=['Any'],
)
