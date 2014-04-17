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

import os
import inspect

from unittest import TestCase

from mock import patch, Mock, call


from gofer.collator import Collator, Module


class Test(object):

    def read(self):
        pass

    def write(self):
        pass


class TestCollator(TestCase):

    def test_init(self):
        collator = Collator()
        self.assertEqual(collator.classes, {})
        self.assertEqual(collator.bound, set())
        self.assertEqual(collator.functions, [])

    @patch('gofer.collator.Collator._Collator__map')
    @patch('gofer.collator.Collator._Collator__functions')
    def test_collate(self, _functions, _map):
        func_globals = {'A': 1}
        _fn1 = Mock()
        _fn1.func_globals = func_globals
        _fn2 = Mock()
        _fn2.func_globals = func_globals
        decorated = [_fn1, _fn2]
        collator = Collator()
        classes, functions = collator.collate(decorated)
        _functions.assert_called_with()
        _map.assert_called_with(func_globals)
        self.assertEqual(id(classes), id(collator.classes))
        self.assertEqual(functions, _functions())

    @patch('gofer.collator.Collator._Collator__classes')
    @patch('gofer.collator.Collator._Collator__methods')
    @patch('gofer.collator.Collator._Collator__function')
    @patch('gofer.collator.Collator._Collator__decorated')
    def test_map(self, _decorated, _function, _methods, _classes):
        func_globals = {'A': 1, 'B': 2}
        methods = [
            'm1',
            'm2',
            'm3',
            'm4',
            'm5',
            'm6',
            'm7',
            'm8',
            'm9'
        ]
        functions = [
            'f1',
            'f2',
            'f3',
            'f4',
            'f5',
            'f6',
            'f7',
            'f8',
            'f9'
        ]
        _classes.return_value = [
            'c1',
            'c2',
            'c3'
        ]
        _methods.side_effect = [
            methods[0:3],
            methods[3:6],
            methods[6:9]
        ]
        _function.side_effect = functions
        _decorated.side_effect = [(fn, None) for fn in functions]
        collator = Collator()
        collator._Collator__map(func_globals)
        _classes.assert_called_with(func_globals)
        _methods.assert_has_calls([call(c) for c in _classes.return_value])
        _function.assert_has_calls([call(m) for m in methods])
        self.assertEqual(collator.bound, set(functions))

    @patch('inspect.isclass')
    def test_classes(self, _isclass):
        func_globals = Mock()
        func_globals.values.return_value = [1, 2, 3]
        _isclass.side_effect = [True, False, True]
        collator = Collator()
        classes = collator._Collator__classes(func_globals)
        _isclass.assert_has_calls([call(c) for c in func_globals.values()])
        self.assertEqual(classes, [1, 3])

    @patch('inspect.getmembers')
    def test_methods(self, _getmembers):
        _getmembers.return_value = [('A', 1), ('B', 2)]
        cls = Mock()
        collator = Collator()
        methods = collator._Collator__methods(cls)
        _getmembers.assert_called_with(cls, inspect.ismethod)
        self.assertEqual(methods, [v for n, v in _getmembers()])

    @patch('inspect.getmembers')
    def test_function(self, _getmembers):
        _getmembers.return_value = [('A', 1)]
        method = Mock()
        collator = Collator()
        function = collator._Collator__function(method)
        _getmembers.assert_called_with(method, inspect.isfunction)
        self.assertEqual(function, _getmembers()[0][1])

    @patch('inspect.getmodule')
    @patch('gofer.collator.Collator._Collator__decorated')
    def test_functions(self, _decorated, _getmodule):
        m1 = Module('m1')
        m2 = Module('m2')
        modules = [m1, m2, m2]
        _decorated.side_effect = lambda x: (x, None)
        _getmodule.side_effect = modules
        collator = Collator()
        for n in range(4):
            name = 'f%d' % n
            fn = Mock(name=name)
            fn.__name__ = name
            collator.functions.append(fn)
        collator.bound.add(collator.functions[1])
        functions = collator._Collator__functions()
        for module, fns in functions.items():
            if module == m1:
                self.assertTrue(hasattr(module, 'f0'))
                self.assertEqual(fns, [(f, None) for f in collator.functions[0:1]])
                continue
            if module == m2:
                self.assertTrue(hasattr(module, 'f2'))
                self.assertTrue(hasattr(module, 'f3'))
                self.assertEqual(fns, [(f, None) for f in collator.functions[2:4]])
                continue

    def test_decorated(self):
        collator = Collator()
        collator.functions = []
        # not found
        fn = collator._Collator__decorated(1)
        self.assertTrue(fn is None)
        # found in list
        collator.functions = [1]
        fn = collator._Collator__decorated(1)
        self.assertEqual(fn, (1, None))
        # found in dictionary
        collator.functions = {1: {'A': 1}}
        fn = collator._Collator__decorated(1)
        self.assertEqual(fn, (1, {'A': 1}))

    def test_list(self):
        decorated = [
            os.path.join,
            Test.read.im_func,
            Test.write.im_func,
        ]
        collator = Collator()
        classes, functions = collator.collate(decorated)
        self.assertEqual(classes, {Test: [(Test.read, None), (Test.write, None)]})
        self.assertEqual(len(functions), 1)
        self.assertEqual(functions.keys()[0].__name__, os.path.__name__)
        self.assertEqual(functions.values()[0], [(os.path.join, None)])

    def test_dictionary(self):
        decorated = {
            os.path.join: {'A': 1},
            Test.read.im_func: {'B': 2},
            Test.write.im_func: {'C': 3},
        }
        collator = Collator()
        classes, functions = collator.collate(decorated)
        self.assertEqual(classes, {Test: [(Test.read, {'B': 2}), (Test.write, {'C': 3})]})
        self.assertEqual(len(functions), 1)
        self.assertEqual(functions.keys()[0].__name__, os.path.__name__)
        self.assertEqual(functions.values()[0], [(os.path.join, {'A': 1})])


class TestModule(TestCase):

    def test_init(self):
        name = 'test'
        mod = Module(name)
        self.assertEqual(mod.__name__, name)

    def test_iadd(self):
        fn = Mock(name='fn')
        fn.__name__ = 'open'
        mod = Module('test')
        mod += fn
        self.assertEqual(mod.open, fn)

    def test_hash(self):
        mod = Module('test')
        self.assertEqual(hash(mod), hash(mod.__name__))

    def test_eq(self):
        self.assertEqual(Module('test'), Module('test'))
        self.assertNotEqual(Module('test'), Module('test2'))
