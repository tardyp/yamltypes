#!/usr/bin/env python
"""This program generates the rst documentation from a list of .meta.yaml files"""

import argparse
import glob
import os
import pprint

from . import yaml


BASE_TYPES = {
    "integer": dict(description=("Integer number.\n\n"
                                 "Example: ``1``, ``-1``, ``123``"), type="base"),
    "boolean": dict(description="Boolean value.\n\nAllowed values: ``True`` or ``False``",
                    type="base"),
    "string": dict(description="Arbitrary string", type="base"),
    "anything": dict(description="No type check is done on this base type.", type="base"),
    "map": dict(description=("Named group of values of the same type.\n\n"
                             "The type should be added in the form of '``mapof<type>s``', "
                             "where type of "
                             "any of the other type. Add a 's' at the end of the type.\n\n"
                             "Example:\n\n"
                             ".. code-block:: yaml\n\n"
                             "    modules: \n"
                             "        type: mapofstrings\n\n"
                             ".. important:: For multiple map (``mapofmapof...``), "
                             "you should add several 's': "
                             "``mapofmapofstringss``, ``mapofmapofintergerss``,....\n"
                             ), type="base"),
    "list": dict(description=("Ordered list of values of the same type. "
                              "Should happen 's' at the end "
                              "(see :ref:`android_map` description)\n\n"
                              "Example:\n\n"
                              ".. code-block:: yaml\n\n"
                              "    the_list:\n"
                              "        type: listofstrings:\n\n"
                              "You can restrict the value used, using the 'value' key. "
                              "For example:\n\n"
                              ".. code-block:: yaml\n\n"
                              "    the_restricted_list_of_strings:\n"
                              "        type: listofstrings:\n"
                              "        values: ['value1', 'value2']:\n"
                              ), type="base"),
    "set": dict(description=("Unordered group of values of the same type, "
                             "where each value can appear only once."), type="base"),
    "dict": dict(description=("Named group of values. Each named value has a specified type.\n\n"
                              "Example:\n\n"
                              ".. code-block:: yaml\n\n"
                              "    the_dict:\n"
                              "        type: dict\n"
                              "        kids:\n"
                              "            first_value:\n"
                              "                type: string\n"
                              "            second_value:\n"
                              "                type: integer\n"
                              ), type="base")
}
known_types = set()


class RstFile(object):

    """
    This File like object implements helper for generating a rst file from a yaml meta spec

    It does not derivate from file to avoid unexpected side effects
    """

    def __init__(self, filename, namespace):
        self.out = open(filename, "w")
        self.numindent = 0
        self.namespace = namespace

    def write(self, s="", forceIndent=None):
        if forceIndent is not None:
            numindent = forceIndent
        else:
            numindent = self.numindent
        if s.endswith("\n"):
            s = s[:-1]
        return self.out.write(" " * numindent + s.replace("\n", "\n" + " " * numindent) + "\n")

    def close(self):
        self.out.close()

    def indent(self):
        self.numindent += 4

    def unindent(self):
        self.numindent -= 4

    def makeTitle(self, title, mark):
        self.write(title)
        self.write(mark * len(title))
        self.write()

    def makeType(self, typ):
        self.write("**Type:** %s" % (typ,))
        self.write()
        self.write()

    def extractCollectionType(self, typ, collection):
        basetype = typ[len(collection):]
        if basetype.endswith("s"):
            basetype = basetype[:-1]
        if basetype in known_types:
            basetype = ":ref:`%s_%s`" % (self.namespace, basetype)  # adds an internal link
        return basetype

    def dumpTypeSpec(self, relpath, v, nodepath):
        if v is None:
            raise ValueError("Empty node: {}".format(relpath))
        if "description" in v:
            self.write("**Description**:")
            self.indent()
            self.write("%s\n\n" % (v['description'],))
            self.unindent()
        if "type" not in v:
            raise ValueError("Missing 'type' key in node '{}': {!r}".format(relpath, v))
        typ = v["type"]
        required = v.get("required", False)
        self.write("**Required:** ``%s``" % (required,))
        self.write()
        self.write("**Default value:** ``%r``" % (v.get('default', None),))
        self.write()
        if 'forbidden' in v:
            self.write("**Forbidden condition:** ``%s``" % (v['forbidden'],))
            self.write()
        known_type = False
        if typ == "base":
            known_type = True
        if typ in known_types:
            known_type = True
            self.makeType(":ref:`%s_%s`" % (self.namespace, typ))
        for collection in ("setof", "listof", "mapof"):
            if typ.startswith(collection):
                known_type = True
                basetype = self.extractCollectionType(typ, collection)
                if not basetype.endswith("dict"):
                    self.makeType(collection.replace("of", " of ") + basetype)
                else:
                    basetype = basetype.replace("dict", "")
                    self.makeType(collection.replace("of", " of") + basetype)
        if "names_type" in v:
            self.write("**Keys type**: ")
            if isinstance(v['names_type'], str):
                self.write(":ref:`%s_%s`" % (self.namespace, v['names_type']))
            else:
                self.indent()
                self.write()
                self.write()
                self.dumpTypeSpec(None, v['names_type'], None)
                self.unindent()
            self.write()
            self.write()
        if "kids" in v:
            known_type = True
            self.write("**Parameters**:")
            self.write()
            keys = list(v["kids"].keys())
            for k in sorted(keys):
                self.indent()
                childpath = relpath
                childnodepath = nodepath
                if relpath is not None:
                    childpath += "_" + k
                    childnodepath += "." + k
                    self.indent()
                    self.write(".. _%s:" % (childpath))
                    self.unindent()
                    self.write()
                self.write("#. ``%s``" % (k,))
                self.write()
                self.write()
                self.indent()
                self.dumpTypeSpec(childpath, v["kids"][k], childnodepath)
                self.unindent()
                self.unindent()
                self.write()
            self.write()
            self.write()
        if not known_type:
            pprint.pprint(v)
        if "values" in v:
            self.write("**Allowed values:**")
            self.write("    ``%s``" % ("``, ``".join(v['values']),))
            self.write()
            self.write()


def loadTypes(paths):
    ret = {}
    for p in paths:
        for fn in glob.glob(os.path.join(p, "*.type.yaml")):
            with open(fn) as y:
                ret[fn.replace(".type.yaml", "")] = yaml.safe_load(y)
    return ret


def columnSeparatedPath(s):
    return s.split(":")


def main():
    def dir_arg(path):
        if os.path.isdir(path):
            return path.rstrip('/')
        raise argparse.ArgumentTypeError('Not a directory: %s' % (path,))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directories', metavar='dirs', type=dir_arg, nargs='+',
                        help='list of directories where to find the .meta.yaml files')
    parser.add_argument('--path', type=columnSeparatedPath,
                        help='paths where to find meta.yaml files', default=[])
    parser.add_argument('--output', type=dir_arg,
                        help='output directory', required=True)
    args = parser.parse_args()
    dumped_types = set()
    for d in args.directories:
        basedir = os.path.basename(d)
        outfn = os.path.join(args.output,
                             basedir + ".rst")
        out = RstFile(outfn, basedir)
        out.makeTitle("YAML documentation for the product '%s'" % (basedir,), "=")
        out.makeTitle("Base types", "~")
        out.write("These are the base types that can be used in the Yaml files.")
        out.write()

        known_types.update(list(BASE_TYPES.keys()))
        types = list(BASE_TYPES.items()) + list(loadTypes(args.path).items())
        types.sort()

        for k, v in types:
            if k not in dumped_types:
                dumped_types.add(k)
                out.write(".. _%s_%s:" % (basedir, k))
                out.write()
                out.write()
                out.makeTitle("``%s``" % (k,), '_')
                out.dumpTypeSpec(basedir + "_" + k, v, basedir + "." + k)
        for fn in sorted(glob.glob(os.path.join(d, "*.meta.yaml"))):
            if "types.meta" in fn:
                continue
            v = yaml.load(open(fn))
            k = os.path.basename(fn).replace(".meta", "")
            out.write(".. _%s_file_type_%s:" % (basedir, k))
            out.write()
            out.write()
            out.makeTitle("``%s``" % (k,), '~')
            if 'root' in v:
                if 'description' not in v['root']:
                    print("warning", fn, "does not have a description")
                out.dumpTypeSpec(basedir + "_" + k, v['root'], basedir + "." + k)

        out.close()
