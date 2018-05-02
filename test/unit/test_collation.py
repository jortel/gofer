# Copyright (c) 2014 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import unittest
import mock

from gofer import collation
from gofer import inspection


THIS_SHOULD_BE_IGNORED = ''


def fn1(name, age):
    pass


def fn2():
    pass


class Person(object):
    name = ''
    age = 0

    def __init__(self, parent=None):
        self.parent = parent

    def walk(self, speed=10):
        pass

    def run(self):
        pass


class Zebra(object):

    def run(self):
        pass


class TestCollator(unittest.TestCase):

    def test_collate(self):
        options = {'A': 1}
        mod = inspection.module(fn1)
        functions = inspection.functions(mod)
        functions.extend(inspection.methods(Person))
        functions = {f[1]: options for f in functions}
        collator = collation.Collator()
        classes, functions = collator(functions)
        self.assertEqual(
            classes,
            [
                collation.Class(
                    Person, methods={
                        m.name: m for m in [
                            collation.Method(Person.walk),
                            collation.Method(Person.run)
                        ]})
            ])
        self.assertEqual(
            functions,
            [
                collation.Module(
                    mod, functions={
                        f.name: f for f in [
                            collation.Function(fn1),
                            collation.Method(fn2)
                        ]})
            ])


class TestModule(unittest.TestCase):

    def test_init(self):
        impl = inspection.module(fn1)
        mod = collation.Module(impl)
        self.assertEqual(mod.name, impl.__name__)
        self.assertEqual(mod.impl, impl)

    def test_operators(self):
        impl = inspection.module(fn1)
        mod = collation.Module(impl)
        # iadd
        fn = collation.Function(fn1)
        mod += fn
        self.assertEqual(list(mod.functions.values())[0], fn)
        # hash
        self.assertEqual(
            hash(mod),
            hash(impl.__name__))
        # index
        self.assertEqual(
            mod['fn1'],
            fn)
        # eq
        self.assertEqual(
            collation.Module(impl),
            collation.Module(impl))
        # neq
        self.assertNotEqual(
            collation.Module(impl),
            collation.Module(mock.Mock(__name__='')))
        # iter
        self.assertEqual(
            list(mod.functions.values()),
            list(mod))


class TestClass(unittest.TestCase):

    def test_init(self):
        impl = Person
        cls = collation.Class(impl)
        self.assertEqual(cls.name, impl.__name__)
        self.assertEqual(cls.impl, impl)

    def test_operators(self):
        impl = Person
        cls = collation.Class(impl)
        # iadd
        method = collation.Method(impl.walk)
        cls += method
        self.assertEqual(list(cls.methods.values())[0], method)
        # hash
        self.assertEqual(
            hash(cls),
            hash(impl.__name__))
        # index
        self.assertEqual(
            cls['walk'],
            method)
        # eq
        self.assertEqual(
            collation.Class(impl),
            collation.Class(impl))
        # lt
        self.assertLess(
            collation.Class(impl),
            collation.Class(Zebra))
        # neq
        self.assertNotEqual(
            collation.Class(impl),
            collation.Class(mock.Mock(__name__='')))
        # iter
        self.assertEqual(
            list(cls.methods.values()),
            list(cls))


class TestFunction(unittest.TestCase):

    def test_function(self):
        fn = collation.Function(fn1)
        self.assertEqual(fn.impl, fn1)
        self.assertEqual(fn.name, fn1.__name__)
        self.assertEqual(fn, collation.Function(fn1))
        self.assertNotEqual(fn, collation.Function(fn2))
        self.assertLess(fn, collation.Function(fn2))
        self.assertEqual(hash(fn1), hash(fn))

    def test_signature(self):
        fn = collation.Function(fn1)
        self.assertEqual('(name, age)', fn.signature)


class TestMethod(unittest.TestCase):

    def test_method(self):
        method = collation.Method(Person.walk)
        self.assertEqual(method.impl, Person.walk)
        self.assertEqual(method.name, Person.walk.__name__)
        self.assertEqual(method, collation.Method(Person.walk))
        self.assertNotEqual(method, collation.Method(Person.run))
        self.assertLess(collation.Method(Person.run), method)
        self.assertEqual(hash(method), hash(Person.walk))

    def test_signature(self):
        method = collation.Method(inspection.get_unbound_function(Person.walk))
        self.assertEqual('(self, speed=10)', method.signature)