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

from unittest import TestCase

from mock import Mock, patch

from gofer.agent.decorator import Action, Actions, Delegate
from gofer.collation import Class, Module, Method, Function


class TestActions(TestCase):

    def test_add(self):
        functions = {}
        fn = '<function>'
        interval = '<interval>'
        with patch('gofer.agent.decorator.Actions.functions', functions):
            Actions.add(fn, interval)
            self.assertEqual(functions, {fn: interval})

    def test_clear(self):
        functions = {}
        fn = '<function>'
        interval = '<interval>'
        with patch('gofer.agent.decorator.Actions.functions', functions):
            Actions.add(fn, interval)
            self.assertEqual(Actions.functions, {fn: interval})
            Actions.clear()
            self.assertEqual(Actions.functions, {})

    @patch('gofer.agent.decorator.Collator.__call__')
    def test_collated(self, collate):
        def fn1(): pass

        def fn2(): pass

        def fn3(): pass

        def fn4(): pass

        class T(object):
            def m1(self): pass

            def m2(self): pass

            def m3(self): pass

            def m4(self): pass

        methods = [
            Method(T.m1, dict(days=30)),
            Method(T.m2, dict(minutes=40)),
            Method(T.m3, dict(hours=10)),
            Method(T.m4, dict(seconds=20)),
        ]
        functions = [
            Function(fn1, dict(days=30)),
            Function(fn2, dict(minutes=40)),
            Function(fn3, dict(hours=10)),
            Function(fn4, dict(seconds=20)),
        ]

        functions = [
            Module(Mock(__name__='M1'), functions={f.name: f for f in functions})
        ]
        classes = [
            Class(Mock(__name__='C1'), methods={m.name: m for m in methods})
        ]

        collate.return_value = (classes, functions)

        actual = sorted(Actions.collated(), key=lambda a: a.name)

        expected = []
        for ns in classes + functions:
            for target in ns:
                expected.append(Action(str(target), target, **target.options))

        expected = sorted(expected, key=lambda a: a.name)
        self.assertEqual(expected, actual)


class TestDelegate(TestCase):

    def test_init(self):
        Delegate.load.append(1)
        Delegate.unload.append(2)
        d = Delegate()
        self.assertEqual(Delegate.load, [])
        self.assertEqual(Delegate.unload, [])
        self.assertEqual(d.load, [1])
        self.assertEqual(d.unload, [2])

    def test_loaded(self):
        d = Delegate()
        d.load = [Mock(), Mock()]
        d.loaded()
        for fn in d.load:
            fn.asssert_called_once_with()

    def test_unloaded(self):
        d = Delegate()
        d.unload = [Mock(), Mock()]
        d.unloaded()
        for fn in d.unload:
            fn.asssert_called_once_with()

    def test_unloaded_failed(self):
        d = Delegate()
        d.unload = [Mock(side_effect=ValueError), Mock()]
        d.unloaded()
        for fn in d.unload:
            fn.asssert_called_once_with()
