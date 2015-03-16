import copy
import logging
import os

from dictns import Namespace

from . import yaml

cactusLog = logging.getLogger(__name__)


class YamlError(ValueError):

    """exception sent in case of any error in the yaml files
    Used to output coherent and understandable error messages
    """

    def __init__(self, path, value, message):
        ValueError.__init__(self, "%s: %s\ncode:\n%s\n"
                            % (path, message, yaml.dump(value, indent=4)))


class CustomizationError(ValueError):
    pass


class Type(object):

    """basic types (str, int, etc)"""

    def __init__(self, name, _type, values=None):
        if values is None:
            values = []
        self.name = name
        self.type = _type
        self.values = values

    def ensure_type(self, path, val):
        if self.maybenull and val is None:
            return
        if self.type == "anything":
            return
        if str(val).lower() == "none":
            return
        if not isinstance(val, self.type):
            raise YamlError(path, val, "should be of type '%s', while it is '%s'." %
                            (str(self.type), type(val)))

    def ensure_values(self, path, val):
        if self.values and val not in self.values:
            raise YamlError(path, val, "'%s' should be one of: %s" % (val,
                                                                      ", ".join(self.values)))

    def match(self, name, val):
        self.ensure_type(name, val)
        self.ensure_values(name, val)


class Container(Type):

    """container types dict,list, listofstrings, listofsetstringss, etc
    """

    def __init__(self, name, type, spec):
        self.name = name
        self.type = type
        self.spec = spec

    def match(self, name, val):
        self.ensure_type(name, val)
        self.iter_and_match(name, val)

    def match_spec(self, spec, name, val):
        try:
            spec.match(name, val)
        except AttributeError as e:
            msg = "Error in {}\n. Message: {}".format(name, e.message)
            raise AttributeError(msg)


class List(Container):

    """ Spec is a Type that is matched against all elements"""

    def iter_and_match(self, path, val):
        for i in xrange(len(val)):
            self.match_spec(self.spec, "%s[%d]" % (path, i),
                            val[i])


class Set(List):

    """ Spec is a Type that is matched against all elements,
        each element can appear only once
    """

    def match(self, path, val):
        Container.match(self, path, val)
        if len(val) != len(set(val)):
            _val = copy.deepcopy(val)
            while len(_val):
                v = _val.pop(0)
                if v in _val:
                    raise YamlError(path, val,
                                    "%s is included several times in a set" % (v,))


class Dict(Container):

    """ spec is a dictionary of Types"""

    def iter_and_match(self, path, val):
        for k, s in self.spec.items():
            if s.required and k not in val:
                raise YamlError(path, val,
                                "needs to define the option '%s', but only has: %r" % (k, val.keys()))
            if s.forbidden and k in val:
                raise YamlError(path, val,
                                "option %s is forbidden" % (k,))
            if s.default is not None and k not in val:
                val[k] = s.default
        for k, v in val.items():
            if k not in self.spec:
                raise YamlError(path, val,
                                "Key '%s' not defined in spec file, should be one of: %r" % (k, self.spec.keys()))
            self.match_spec(self.spec[k], path + "." + k, v)


class Map(Container):

    """ a Map is like a named list. All elements have the same spec.
    names_type is an optionnal argument to verify the type of the
    names of the list."""

    def __init__(self, name, type, spec, names_type=None):
        self.names_type = names_type
        Container.__init__(self, name, type, spec)

    def iter_and_match(self, path, val):
        if self.names_type is not None:
            n = self.name + "_names"
            keyst = Set(n, list, self.names_type)
            keyst.maybenull = False
            keyst.match(n, val.keys())
        if val is None:
            raise YamlError(path, val, "Invalid empty value !")
        for k, v in val.items():
            self.match_spec(self.spec, path + "." + k, v)


def _parseYaml(content):
    y = yaml.load(content)
    if y is None:
        return Namespace({})
    return y


def _parseOrderedYaml(content):
    y = yaml.load(content, Loader=yaml.OrderedMapAndDuplicateCheckLoader)
    if y is None:
        return Namespace({})
    return y


def yamlLoad(fn):
    path = os.path.basename(fn)
    try:
        content = open(fn, "r").read()
        return _parseYaml(content)
    except Exception as e:
        raise YamlError(path, "", str(e))


def orderedYamlLoad(fn):
    path = os.path.basename(fn)
    try:
        content = open(fn, "r").read()
        return _parseOrderedYaml(content)
    except Exception as e:
        raise YamlError(path, "", str(e))

def findSpec(fn, yamltypes_dirs, exists=os.path.exists):
    def findMetaYaml(fn):
        specfn = fn + ".meta.yaml"
        if exists(specfn):
            return specfn
        return None
    basespecfn = os.path.splitext(fn)[0]
    specfn = findMetaYaml(basespecfn)
    if specfn:
        return specfn
    basespecfn = os.path.basename(basespecfn)
    while basespecfn:
        for yamltypes_dir in yamltypes_dirs:
            specfn = findMetaYaml(os.path.join(yamltypes_dir, basespecfn))
            if specfn:
                return specfn
        if "." not in basespecfn:
            return None
        basespecfn = basespecfn.split(".", 1)[1]

class YamlConfigBuilder(object):

    def _yamlLoad(self, fn):
        return yamlLoad(fn)


    def __init__(self, fn, customizations=None, additionnal_types=None,
                 specfn=None, yamltypes_dirs=[], needSpec=True):
        if customizations is None:
            customizations = []
        self._dict = self._yamlLoad(fn)
        self.mixCustomizations(os.path.basename(fn), customizations)
        self._ns = Namespace(self._dict)
        self.types = {}
        if not specfn:
            specfn = findSpec(fn, yamltypes_dirs)
        if specfn is not None:
            specbasedir = os.path.dirname(specfn)
            if additionnal_types:
                self.importTypes(additionnal_types)
            spec = self._yamlLoad(specfn)
            tname = os.path.basename(fn.replace(".yaml", ""))
            if 'imports' in spec:
                for additionnal_type in spec['imports']:
                    for yamltypes_dir in yamltypes_dirs:
                        additionalfn = os.path.abspath(os.path.join(yamltypes_dir, additionnal_type))
                        if not os.path.exists(additionalfn):
                            additionalfn = os.path.abspath(os.path.join(specbasedir,
                                                                        "types",
                                                                        additionnal_type))
                        if not os.path.exists(additionalfn):
                            raise Exception("Unable to find imports {!r}".format(additionnal_type))
                        self.importTypes(additionalfn)
            t = self.createType(tname, tname, spec["root"])
            t.match(tname, self._dict)
            # rebuild the Namespace, self._dict may contain
            # more data, filled by the default

            self._ns = Namespace(self._dict)
        else:
            if needSpec:
                raise ValueError("no spec found for %s" % (fn, ))

    @staticmethod
    def applyCustomizationRule(obj, selector, value):
        orig_selector = selector
        while selector.find(".") >= 0:
            key, selector = selector.split(".", 1)
            if key not in obj:
                raise CustomizationError("selector: '%s' wants to traverse non-existing key '%s' in: %s"
                                         % (orig_selector, key, obj.keys()))
            obj = obj[key]
            if not isinstance(obj, dict):
                raise CustomizationError("selector: '%s' wants to traverse a non dictionary object "
                                         "'%s' in: %s" % (orig_selector, key, obj))
        action = "REPLACE"
        if selector.find(":") >= 0:
            selector, action = selector.split(":", 1)
            action = action.strip()

        if selector and selector not in obj and action not in ["REPLACE", "DELETEIF"]:
            raise CustomizationError("selector: '%s' wants to modify non-existing key '%s' at: %s"
                                     % (orig_selector, selector, obj))

        if action in ["REPLACE", "DELETEIF"] and selector and selector not in obj:
            cactusLog.debug("Selector: %r, object doesn't have the selector yet, Action: %r, Value: %r",
                            selector, action, value)
        elif selector:
            cactusLog.debug("Selector: %r, object: %r, Action: %r, Value: %r", selector, obj[selector], action, value)

        if action == "REPLACE" and selector:
            obj[selector] = value

        elif action == "REPLACE" and not selector and isinstance(obj, list):
            if not isinstance(value, list):
                raise CustomizationError("can only replace list by other list, not %r"
                                         % (value))
            del obj[:]
            obj.extend(value)

        elif action == "REPLACE" and not selector and isinstance(obj, dict):
            if not isinstance(value, dict):
                raise CustomizationError("can only replace dict by other dict, not %r"
                                         % (value))
            obj.clear()
            obj.update(value)

        elif action in ["DEL", "DELETE", "DELETEIF"]:
            if value is not None:
                raise CustomizationError("selector: '%s' value is ignored because it is a delete"
                                         % (orig_selector,))
            if selector:
                if selector in obj:
                    del obj[selector]
            else:
                # DELETE_ALL_ACTION
                obj.clear()

        elif action == "APPEND":
            obj[selector].append(value)

        elif action == "EXTEND":
            obj[selector].extend(value)

        elif action == "POP":
            obj[selector].pop(value)

        elif action == "REMOVE":
            if isinstance(value, list):
                for v in value:
                    obj[selector].remove(v)
            else:
                obj[selector].remove(value)
        else:
            raise CustomizationError("selector: unsupported action '%s'"
                                     % (orig_selector,))

    def mixCustomizations(self, fn, customizations):
        def doCustomization(selector, value):
            try:
                YamlConfigBuilder.applyCustomizationRule(self._dict, selector,
                                                         value)
            except CustomizationError as e:
                raise CustomizationError("Applying %s in %s:\n %s" %
                                         (customfn, fn, str(e)))

        DELETE_ALL_ACTION = ":DELETE"
        for customization in customizations:
            basedir = os.path.dirname(customization)
            customfn = os.path.basename(customization)
            custom = Namespace(self._yamlLoad(customization))
            if custom:
                if "imports" in custom:
                    import_customs = [os.path.realpath(os.path.join(basedir, cnfn))
                                      for cnfn in custom['imports']]
                    self.mixCustomizations(fn, import_customs)
                if fn in custom and custom[fn] is not None:
                    cactusLog.debug("Applying customization: %s", custom[fn])
                    # DELETE_ALL must be done first
                    if DELETE_ALL_ACTION in custom[fn]:
                        value = custom[fn][DELETE_ALL_ACTION]
                        selector = DELETE_ALL_ACTION
                        doCustomization(selector, value)
                    for selector, value in custom[fn].iteritems():
                        if DELETE_ALL_ACTION == selector:
                            continue
                        doCustomization(selector, value)

    def createType(self, path, name, spec):
        spec = copy.deepcopy(spec)
        try:
            iter(spec)
        except TypeError:
            raise YamlError(path, spec, "Item should be iterable but is of type %s" % (type(spec),))
        if "type" not in spec:
            raise YamlError(path, spec, "type spec must contain a 'type' key.")
        t = spec["type"]

        def get_component_type(t):
            t = t[t.index("of") + 2:]
            # manage the case: listoflistsoflistsofsetsofstrings
            for i in "listsof setsof mapsof".split():
                if t.startswith(i):
                    return t.replace("sof", "of", 1)
            return t[:-1]  # remove final 's'

        def getType(kt):
            try:
                return self.types[kt]
            except KeyError as e:
                raise KeyError("Invalid type {e} for node '{node}'. Available: {types!r}"
                               .format(node=path, e=e, types=self.types.keys()))

        ret = None
        for tname, ttype in dict(string=str, integer=int,
                                 boolean=bool, float=float,
                                 anything="anything").items():
            if t == tname:
                kw = {}
                for k in "values".split():
                    if k in spec:
                        kw[k] = spec[k]
                ret = Type(name, ttype, **kw)

        if ret:
            pass
        elif t.startswith("listof"):
            tname = get_component_type(t)
            spec["type"] = tname
            ret = List(name, list,
                       self.createType(path + "[]." + tname,
                                       tname, spec))
        elif t.startswith("mapof"):
            tname = get_component_type(t)
            spec["type"] = tname
            names_type = None
            if "names_type" in spec.keys():
                kt = spec["names_type"]
                if isinstance(kt, basestring):
                    names_type = getType(kt)
                else:
                    names_type = self.createType(path + "[name]." + tname,
                                                 tname, kt)

            ret = Map(name, dict,
                      self.createType(path + "[]." + tname,
                                      tname, spec),
                      names_type=names_type)
        elif t.startswith("dict"):
            kids = {}
            if 'kids' not in spec:
                raise YamlError(path, spec, "dict type has no 'kids': %r" % (spec,))
            if spec["kids"] is None:
                raise YamlError(path, spec,
                                "spec[\"kids\"] is None")
            for k, v in spec["kids"].items():
                kids[k] = self.createType(path + "." + k, k, v)
            ret = Dict(name, dict, kids)
        elif t.startswith("setof"):
            tname = get_component_type(t)
            spec["type"] = tname
            ret = Set(name, list, self.createType(path + "[]." + tname,
                                                  tname, spec))
        elif t not in self.types:
            raise YamlError(path, spec, "unknown type: %s (supported: %s)" % (t, ", ".join(self.types)))
        else:
            ret = copy.deepcopy(self.types[t])
        for k in "required default forbidden maybenull".split():
            if k in spec:
                # for required and forbidden, we allow conditionnal requirement
                # depending on content of the data
                if k in "required forbidden maybenull".split() and isinstance(spec[k], str):
                    try:
                        spec[k] = eval(spec[k], dict(),
                                       dict(self=self._ns))
                    except Exception as e:
                        raise YamlError(path, spec[k],
                                        "issue with python expression in yaml:\n" + str(e))
                setattr(ret, k, spec[k])
            else:
                setattr(ret, k, None)
        return ret

    def importTypes(self, fn):
        path = os.path.basename(fn)
        if os.path.exists(fn):
            types_to_import = list(self._yamlLoad(fn).items())
            problematics = []
            while types_to_import and len(problematics) != len(types_to_import):
                name, spec = types_to_import.pop(0)
                try:
                    self.types[name] = self.createType(path + ":" + name, name, spec)
                    problematics = []
                except Exception as e:
                    if isinstance(e, TypeError):
                        raise
                    problematics.append(e)
                    types_to_import.append((name, spec))
            if problematics:
                raise problematics[0]


class OrderedYamlConfigBuilder(YamlConfigBuilder):

    def _yamlLoad(self, fn):
        return orderedYamlLoad(fn)


def YamlConfig(*args, **kw):
    b = YamlConfigBuilder(*args, **kw)
    return b._ns


def OrderedYamlConfig(*args, **kw):
    b = OrderedYamlConfigBuilder(*args, **kw)
    return b._ns
