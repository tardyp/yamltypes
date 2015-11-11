####################################################################################################
#
# Safe Yaml Loader
#
####################################################################################################
#
# This helper module allow you to load a Yaml module with the following enhancement compared to the
# PyYaml module:
#
#   - use libyaml (C library) if available on your system, if not, it will use the Yaml loader
#     writen in python,
#   - check for duplicate keys in dictionary. PyYaml 'constructor' doesn't do check on duplicates,
#     so we end up with sometimes having several keys in the yaml file at the same level of a
#     mapping. This is not allowed by the Yaml Spec but there were no check on PyYaml to cover this
#     issue.
#
# These feature are added by the usage of the loader class ``yaml.DuplicateCheckLoader`` by default
# in place of ``yaml.Loader`` for the ``yaml.load()`` method, and ``yaml.SafeDuplicateCheckLoader``
# in place of ``yaml.SafeLoader`` for the ``yaml.safe_load()`` method.
#
# In addition, this module provides the optional loader ``yaml.OrderedMapAndDuplicateCheckLoader``
# which add:
#   - map are by default not ordered. This modules enforce the use of OrderedDict when loading a
#     "map" from the Yaml. Yaml maps were loaded as dictionaries which does not guarantee the
#     orderness. Using OrderedDict allows to guarantee that the order within the yaml file is kept
#     in the internal structure. Comparison against dict is still legal, and will be done in an
#     unordered way, but iteration in the dictionary **is** ordered, using iterators, .keys(),
#     .values() or .items().
#
#     (you also have ``yaml.SafeOrderedMapAndDuplicateCheckLoader`` for use with ``yaml.safe_load``)
#
# This has a minor cost on performance, mainly due to the use of OrderedDict. Preliminary measures
# shows negative impact about 25% compared to the regular PyYaml parser with libyaml.
#
# Usage:
# ------
#
# Simply replace all occurences of::
#
#   import yaml
#
# with::
#
#   from yamltypes import yaml
#
# and continue working with this yaml module as you would do with the PyYaml module::
#
#   yaml_content = yaml.load(file.read())
#
#
# To use OrderedMapAndDuplicateCheckLoader::
#
#   yaml_content = yaml.load(file.read(), Loader=yaml.OrderedMapAndDuplicateCheckLoader)
#
#
# Notes:
#  - This module has been validated on python 2.7 ONLY
#  - It is intended to be used like yaml, so we inject all the "exports" from the yaml module into
#    this one, that's why we import all other dependencies with the '_' prefix.
#
####################################################################################################
from __future__ import absolute_import
# absolute_import enforce the import of the real yaml loader, and not reimport myself!


import logging as _logging

# injecting the yaml content into the current yaml module
# This causes the pyflakes error:
#   xutils/yaml.py:69: 'from yaml import *' used; unable to detect undefined names
from yaml import *
from yaml.constructor import ConstructorError

_yamlLog = _logging.getLogger(__name__)

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

    _yamlLog.warning('Using Python implementation of YAML, make sure '
                       'libyaml-dev is installed in your virtual environment')

try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict

class _LastUpdatedOrderedDict(OrderedDict):

    '''
    Store items in the order the keys were last added
    Extracted from the OrderedDict receipes:

        https://docs.python.org/2/library/collections.html#ordereddict-examples-and-recipes

    > This ordered dictionary variant remembers the order the keys were last inserted. If a new
    > entry overwrites an existing entry, the original insertion position is changed and moved to
    > the end.
    '''

    def __setitem__(self, key, value):
        if key in self:
            del self[key]
        OrderedDict.__setitem__(self, key, value)

    def __repr__(self):
        return dict(self).__repr__()

class DuplicateCheckLoader(Loader):

    '''
    I am a special Loader that raises an exception when a Yaml file defines a key that has been
      already defined at the same level of the current mapping. This ensure you don't have duplicate
      key in your Yaml file
    '''

    def _getMap(self):
        return {}

    def construct_yaml_map(self, node):
        data = self._getMap()
        yield data
        value = self.construct_mapping(node)
        data.update(value)

    def construct_mapping(self, node, deep=False):
        if not isinstance(node, MappingNode):
            raise ConstructorError(None, None,
                                   "expected a mapping node, but found %s" % node.id,
                                   node.start_mark)
        mapping = self._getMap()
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            try:
                hash(key)
            except TypeError as exc:
                raise ConstructorError("while constructing a mapping", node.start_mark,
                                       "found unacceptable key (%s)" % exc, key_node.start_mark)
            value = self.construct_object(value_node, deep=deep)
            if key in mapping:
                raise ConstructorError("while constructing a mapping", node.start_mark,
                                       "found already in-use key (%s)" % key, key_node.start_mark)

            mapping[key] = value
        return mapping


class SafeDuplicateCheckLoader(SafeLoader):

    '''
    I am a special Loader that raises an exception when a Yaml file defines a key that has been
      already defined at the same level of the current mapping. This ensure you don't have duplicate
      key in your Yaml file
    '''

    def _getMap(self):
        return {}

    def construct_yaml_map(self, node):
        data = self._getMap()
        yield data
        value = self.construct_mapping(node)
        data.update(value)

    def construct_mapping(self, node, deep=False):
        if not isinstance(node, MappingNode):
            raise ConstructorError(None, None,
                                   "expected a mapping node, but found %s" % node.id,
                                   node.start_mark)
        mapping = self._getMap()
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            try:
                hash(key)
            except TypeError as exc:
                raise ConstructorError("while constructing a mapping", node.start_mark,
                                       "found unacceptable key (%s)" % exc, key_node.start_mark)
            value = self.construct_object(value_node, deep=deep)
            if key in mapping:
                raise ConstructorError("while constructing a mapping", node.start_mark,
                                       "found already in-use key (%s)" % key, key_node.start_mark)

            mapping[key] = value
        return mapping


class OrderedMapAndDuplicateCheckLoader(DuplicateCheckLoader):

    '''
    I am a special Loader that does the following
    - raises an exception when a Yaml file defines a key that has been already defined at the same
      level of the current mapping. This ensures you do not have a duplicate key in your Yaml file
    - guarantees orderness of mapping per default, using OrderedDict.
    '''

    def _getMap(self):
        return _LastUpdatedOrderedDict()


class SafeOrderedMapAndDuplicateCheckLoader(SafeDuplicateCheckLoader):

    '''
    I am a special Loader that does the following
    - raises an exception when a Yaml file defines a key that has been already defined at the same
      level of the current mapping. This ensures you do not have a duplicate key in your Yaml file
    - guarantees orderness of mapping per default, using OrderedDict.
    '''

    def _getMap(self):
        return _LastUpdatedOrderedDict()


# Overwrite the map creation constructors
OrderedMapAndDuplicateCheckLoader.add_constructor(
    'tag:yaml.org,2002:map',
    OrderedMapAndDuplicateCheckLoader.construct_yaml_map)
OrderedMapAndDuplicateCheckLoader.add_constructor(
    'tag:yaml.org,2002:python/dict',
    OrderedMapAndDuplicateCheckLoader.construct_yaml_map)

# Overwrite the map creation constructors (safe loaders)
SafeOrderedMapAndDuplicateCheckLoader.add_constructor(
    'tag:yaml.org,2002:map',
    SafeOrderedMapAndDuplicateCheckLoader.construct_yaml_map)
SafeOrderedMapAndDuplicateCheckLoader.add_constructor(
    'tag:yaml.org,2002:python/dict',
    SafeOrderedMapAndDuplicateCheckLoader.construct_yaml_map)

# Overwrite the map creation constructors
DuplicateCheckLoader.add_constructor(
    'tag:yaml.org,2002:map',
    DuplicateCheckLoader.construct_yaml_map)
DuplicateCheckLoader.add_constructor(
    'tag:yaml.org,2002:python/dict',
    DuplicateCheckLoader.construct_yaml_map)

# Overwrite the map creation constructors (safe loaders)
SafeDuplicateCheckLoader.add_constructor(
    'tag:yaml.org,2002:map',
    SafeDuplicateCheckLoader.construct_yaml_map)
SafeDuplicateCheckLoader.add_constructor(
    'tag:yaml.org,2002:python/dict',
    SafeDuplicateCheckLoader.construct_yaml_map)

_orig_load = load
_orig_safe_load = safe_load


def _load(*args, **kwargs):
    '''
    Overrides yaml.load.

    Force usage of DuplicateCheckLoader instead of yaml.Loader as default loader
    '''
    if "Loader" not in kwargs:
        kwargs["Loader"] = DuplicateCheckLoader
    return _orig_load(*args, **kwargs)


def _safeLoad(*args, **kwargs):
    '''
    Overrides yaml.safe_load.

    Force usage of DuplicateCheckLoader instead of yaml.Loader as default loader
    '''
    if "Loader" not in kwargs:
        kwargs["Loader"] = SafeDuplicateCheckLoader
    return _orig_safe_load(*args, **kwargs)

load = _load
safe_load = _safeLoad
