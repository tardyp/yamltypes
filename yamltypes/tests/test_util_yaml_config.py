# This file is part of Buildbot.  Buildbot is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# Copyright Buildbot Team Members
from __future__ import absolute_import

import os

from .. import yaml

from dictns import Namespace
from textwrap import dedent
from unittest import TestCase

from ..yamlconfig import OrderedYamlConfig
from ..yamlconfig import YamlConfig
from ..yamlconfig import findSpec
from ..yamlconfig import YamlConfigBuilder
from ..yamlconfig import _parseYaml


class BaseTestCase(TestCase):
    def assertRaisesWithMessage(self, exceptionClass, expectedMessage, callableObj, *args, **kw):
        '''
        I can be used to check if a given function (normal or defered) raised with a given message.

        Note: You cannot use an inlineCallbacks as callableObj. Please use
        assertInlineCallbacksRaisesWithMessage.
        '''
        try:
            callableObj(*args, **kw)
        except exceptionClass as err:
            self.assertIn(expectedMessage, str(err))
            return
        raise Exception("%s not raised" % (exceptionClass,))

    def assertIn(self, item, iterable):
        self.assertTrue(item in iterable,
                        msg="{item} not found in {iterable}"
                             .format(item=item,
                                     iterable=iterable))

class TestYamlConfig(BaseTestCase):

    def openYaml(self, fn, customizations=None):
        if customizations is None:
            customizations = []
        specfn = None

        def findFile(fn):
            return os.path.join(os.path.dirname(__file__), "test_db", "yaml_config",
                                fn + ".yaml")
        fn = findFile(fn)
        customizations = [findFile(_fn) for _fn in customizations]
        if "fail" in fn:
            specfn = fn[:fn.index(".fail")] + ".meta.yaml"

        typefn = None
        yamltypes_dirs = None
        if "typeimports" in fn:
            yamltypes_dirs = [os.path.join(os.path.dirname(__file__), "test_db", "yaml_config",
                                           "types")]
        if "complex" in fn:
            typefn = os.path.join(os.path.dirname(__file__), "test_db", "yaml_config",
                                  "types.meta.yaml")
        return YamlConfig(fn, customizations=customizations, specfn=specfn,
                          additionnal_types=typefn, yamltypes_dirs=yamltypes_dirs)

    def failTest(self, fn, failtest, customizations=None):
        if customizations is None:
            customizations = []
        failed = False
        res = None
        try:
            res = self.openYaml(fn, customizations=customizations)
        except Exception as e:
            import traceback
            if failtest not in str(e):
                traceback.print_exc()
            self.assertIn(failtest, str(e))
            failed = True
        self.assertTrue(failed, "should have failed, but got: " + str(res))

    def test_basic(self):
        y = self.openYaml("basic")
        self.failIf(y.field1 != "OK")

    def test_basic_invalidKey(self):
        self.failTest("basic.fail1", "Key 'field2' not defined in spec file, should be one of: ['field1']")

    def test_basic_inValues(self):
        self.failTest("basic.fail2", "should be one of")

    def test_complex(self):
        self.openYaml("complex")

    def test_complexDefault(self):
        y = self.openYaml("complex")
        self.assertEqual(y.slaves['l1site'].caps.speed, "fast")

    def test_complex_badlocation(self):
        self.failTest("complex.fail1", "should be one of")

    def test_complex_duplicateInSet(self):
        self.failTest("complex.fail2", "is included several times in a set")

    def test_complex_missingRequired(self):
        self.failTest("complex.fail3", "needs to define the option 'location'")

    def test_complex_missingRequired2(self):
        self.failTest("complex.fail4", "needs to define the option 'builder'")

    def test_complex_multiple_append_success(self):
        s = self.openYaml("complex", customizations=["complex.multiple_append"])
        self.assertEqual(s.slaves.l4site.slaves, ['buildbot1build',
                                                  'buildbot6build',
                                                  'buildbot5build',
                                                  'buildbot8build',
                                                  'buildbot7build',
                                                  'buildbot10build',
                                                  'buildbot9build',
                                                  ]
                         )
        self.assertEqual(s.slaves.l1site.new_item1, 'hello1')
        self.assertEqual(s.slaves.l1site.new_item2, 'hello2')

    def test_funny(self):
        self.openYaml("funny_complex")

    def test_funnyDuplicate(self):
        self.failTest("funny_complex.fail1", "is included several times in a set")

    def test_conditionnal_required(self):
        self.openYaml("conditionnal_required")

    def test_conditionnal_required_absent(self):
        self.failTest("conditionnal_required.fail1", "needs to define the option 'field1'")

    def test_conditionnal_notrequired(self):
        self.openYaml("conditionnal_required.fail2")

    def test_conditionnal_forbidden(self):
        self.failTest("conditionnal_required.fail3", "option field1 is forbidden")

    def test_map_keys_invalid(self):
        self.failTest("map_with_keys_complex.fail",
                      "'invalid_key' should be one of: l1, l2, l3, l4, l5, l6")

    def test_map_keys_ok(self):
        self.openYaml("map_with_keys_complex")

    def test_type_import(self):
        self.openYaml("typeimports")

    def test_type_import_bad(self):
        self.failTest("typeimports.fail", "typeimports.fail.foo[0]: 'foo' should be one of: bar")

    def test_customization(self):
        y = self.openYaml("complex", customizations=["complex.customization"])
        self.assertEqual(y.slaves.l3site.caps.location, "l3")
        self.assertEqual(y.slaves.l1site.caps.location, "l4")

    def test_customization2(self):
        y = self.openYaml("complex", customizations=["complex.customization2"])
        self.assertEqual(y.slaves.l4site.caps.location, "l2")

    def test_customization_import(self):
        y = self.openYaml("complex", customizations=["complex.customization.import"])
        self.assertEqual(y.slaves.l4site.caps.location, "l2")

    def test_customization3(self):
        y = self.openYaml("complex", customizations=["complex.customization3"])
        self.assertEqual(y.slaves.l4site.slaves, ['buildbot1build', 'buildbot3build'])

    def test_customization4(self):
        y = self.openYaml("complex", customizations=["complex.customization4"])
        self.assertEqual(y.slaves.l4site.slaves, [])

    def test_customization_fail(self):
        self.failTest("complex", "'l123' should be one of: l1, l2, l3, l4, l5, l6",
                      customizations=["complex.customization.fail"])


class TestFindSpec(BaseTestCase):
    def testFindSpec_basic(self):
        def exists(s):
            return s == "a.meta.yaml"
        self.assertEqual(findSpec("a.yaml", [], exists=exists), "a.meta.yaml")

    def testFindSpec_in_path(self):
        expected = "b/a.meta.yaml"

        def exists(s):
            return s == expected
        self.assertEqual(findSpec("a.yaml", ["c", "b"], exists=exists), expected)

    def testFindSpec_not_found(self):
        expected = "b/a.meta.yaml"

        def exists(s):
            return s == expected
        self.assertEqual(findSpec("a.yaml", ["c", "d"], exists=exists), None)

    def testFindSpec_subtype(self):
        expected = "d/a.meta.yaml"

        def exists(s):
            return s == expected
        self.assertEqual(findSpec("foo.a.yaml", ["c", "d"], exists=exists), expected)


class TestCustomizationRuleSyntax(BaseTestCase):

    def testYamlLoadSimple(self):
        '''
        I test the yaml loading procedure (ie, loading text and parsing it as Yaml and then
        converted to Namespace)
        '''
        yaml_content = dedent("""
                a:
                    b:
                        c:
                    d:
                e:
                f:
            """).strip()
        c = _parseYaml(yaml_content)
        self.assertEqual(c, {'a': {'b': {'c': None}, 'd': None}, 'e': None, 'f': None})

    def testYamlLoadCustomizationSyntax(self):
        yaml_content = dedent("""
                a:
                    b:
                        c:APPEND: cc
                    d:DEL:
                e:DEL:
                f:
            """).strip()
        c = _parseYaml(yaml_content)
        self.assertEqual(c, {'a': {'b': {'c:APPEND': 'cc'}, 'd:DEL': None}, 'e:DEL': None, 'f': None})

    def testYamlLoadCustomizationBadSyntax(self):
        yaml_content = dedent("""
                a: DELETE
            """).strip()
        c = _parseYaml(yaml_content)
        self.assertEqual(c, {'a': 'DELETE'})

        yaml_content = dedent("""
                a: APPEND:a
            """).strip()
        c = _parseYaml(yaml_content)
        self.assertEqual(c, {'a': 'APPEND:a'})

        yaml_content = dedent("""
                a: APPEND: a
            """).strip()
        self.assertRaises(yaml.scanner.ScannerError, _parseYaml, yaml_content)

    def oneTest(self, rule, value):
        obj = dict(a=dict(b=1, c=[1, 2, 3]))
        # applyCustomizationRule does not require Namespace
        YamlConfigBuilder.applyCustomizationRule(obj, rule, value)
        # return Namespace to ease test readability
        return Namespace(obj)

    def test_applyCustomizationRuleFirstKey(self):
        obj = self.oneTest("a", 2)
        self.assertEqual(obj.a, 2)

    def test_applyCustomizationRuleReplace1(self):
        obj = self.oneTest("a.b", 2)
        self.assertEqual(obj.a.b, 2)

    def test_applyCustomizationRuleReplace2(self):
        obj = self.oneTest("a.c", [1, 2])
        self.assertEqual(obj.a.c, [1, 2])

    def test_applyCustomizationRuleReplace3(self):
        obj = self.oneTest("a.c:REPLACE", [1, 2])
        self.assertEqual(obj.a.c, [1, 2])

    def test_applyCustomizationRuleReplaceWholeDict(self):
        obj = self.oneTest(":REPLACE", {'k': 1})
        self.assertEqual(obj, {'k': 1})

    def test_applyCustomizationRuleReplaceWholeList(self):
        obj = [1, 2, 3, 4]
        # applyCustomizationRule does not require Namespace
        YamlConfigBuilder.applyCustomizationRule(obj, ":REPLACE", [5])
        # return Namespace to ease test readability
        obj = Namespace(obj)
        self.assertEqual(obj, [5])

    def test_applyCustomizationRuleReplaceWholeListBad(self):
        obj = [1, 2, 3, 4]
        # applyCustomizationRule does not require Namespace
        self.assertRaisesWithMessage(
            ValueError, "can only replace list by other list, not {'a': 6}",
            lambda: YamlConfigBuilder.applyCustomizationRule(obj, ":REPLACE", {'a': 6}))

    def test_applyCustomizationRuleReplaceWholeDictBad(self):
        self.assertRaisesWithMessage(
            ValueError, "can only replace dict by other dict, not [5]",
            lambda: self.oneTest(":REPLACE", [5]))

    def test_applyCustomizationRuleDel(self):
        obj = self.oneTest("a.c:DEL", None)
        self.assertRaises(AttributeError, lambda: obj.a.c)

    def test_applyCustomizationRuleDeleteNode(self):
        obj = self.oneTest("a:DELETE", None)
        self.assertRaises(AttributeError, lambda: obj.a.c)

    def test_applyCustomizationRuleDeleteMissingNode(self):
        self.assertRaisesWithMessage(
            ValueError,
            "a.d:DELETE' wants to modify non-existing key 'd' at:",
            lambda: self.oneTest("a.d:DELETE", None))

    def test_applyCustomizationRuleDeleteifMissingNode(self):
        # Should not raise an exception
        self.oneTest("a.d:DELETEIF", None)

    def test_applyCustomizationRuleDelNode(self):
        obj = self.oneTest("a:DEL", None)
        self.assertRaises(AttributeError, lambda: obj.a)

    def test_applyCustomizationRuleDelAll(self):
        obj = self.oneTest(":DEL", None)
        self.assertEqual(obj, {})

    def test_applyCustomizationRuleAppend(self):
        obj = self.oneTest("a.c:APPEND", 4)
        self.assertEqual(obj.a.c, [1, 2, 3, 4])

    def test_applyCustomizationRuleMultipleAppend(self):
        obj = dict(a=dict(b=1, c=[1, 2, 3]))
        YamlConfigBuilder.applyCustomizationRule(obj, "a.c:APPEND", 4)
        YamlConfigBuilder.applyCustomizationRule(obj, "a.c:APPEND", 5)
        obj = Namespace(obj)
        self.assertEqual(obj.a.c, [1, 2, 3, 4, 5])

    def test_applyCustomizationRulePop(self):
        obj = self.oneTest("a.c:POP", 2)
        self.assertEqual(obj.a.c, [1, 2])

    def test_applyCustomizationRuleRemove(self):
        obj = self.oneTest("a.c:REMOVE", 2)
        self.assertEqual(obj.a.c, [1, 3])
        obj = self.oneTest("a.c:REMOVE", 2)
        self.assertEqual(obj.a.c, [1, 3])

    def test_applyCustomizationRuleRemoveList(self):
        obj = self.oneTest("a.c:REMOVE", [1, 2])
        self.assertEqual(obj.a.c, [3])

    def test_applyCustomizationRuleBadCommand(self):
        self.assertRaisesWithMessage(ValueError, "selector: unsupported action 'a.c:BADACTION'",
                                     lambda: self.oneTest("a.c:BADACTION", None))

    def test_applyCustomizationRuleBadKey(self):
        self.assertRaisesWithMessage(ValueError, "selector: 'b.c:DEL' wants to traverse "
                                     "non-existing key 'b' in: ['a']",
                                     lambda: self.oneTest("b.c:DEL", None))

    def test_applyCustomizationRuleBadKey2(self):
        self.assertRaisesWithMessage(ValueError, "selector: 'a.b.c:DEL' wants to traverse "
                                     "a non dictionary object 'b' in: 1",
                                     lambda: self.oneTest("a.b.c:DEL", None))


class TestYamlLoader(BaseTestCase):

    def testDuplicateKeyAreForbidden(self):
        yaml_content = dedent("""
                a: 1
                a: 2
            """).strip()
        self.assertRaises(yaml.constructor.ConstructorError, _parseYaml, yaml_content)

    def _testOrderedKeysInNamespace(self):
        # Test is disabled, Namespace doesn't keep the reordering of the map
        d = OrderedYamlConfig(os.path.join(os.path.dirname(__file__), "test_db", "yaml_config",
                                           "ordered_yaml.yaml"))
        # Unordered test
        self.assertEqual(d, {
            "a": 2,
            "b": 1,
            "c": None,
            "f": 8,
            "t": {
                "t1": 1,
                "t2": 3,
                "t3": 2,
            },
            "z": 9
        })
        self.assertEqual(list(d.keys()), ['b', 'a', 'c', 'z', 'f', 't'])
        self.assertEqual(list(d.t.keys()), ['t1', 't3', 't2'])
    _testOrderedKeysInNamespace.skip = "Namespace doesn't keep OrderedDict"
