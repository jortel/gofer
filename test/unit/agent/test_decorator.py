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

from gofer.agent.decorator import Actions, Delegate


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

    @patch('gofer.agent.decorator.Action')
    @patch('gofer.agent.decorator.Collator.collate')
    def test_collated(self, collate, action):
        functions = (
            (Mock(__name__='m1'), dict(days=30)),
            (Mock(__name__='m2'), dict(minutes=40)),
            (Mock(__name__='fn1'), dict(hours=10)),
            (Mock(__name__='fn2'), dict(seconds=20)),
        )
        class_1 = Mock(__name__='class_1')
        mod_1 = Mock(__name__='mod_1')
        collate.return_value = (
            {class_1: functions[0:2]},
            {mod_1: functions[2:4]}
        )
        actions = [
            Mock(),
            Mock(),
            Mock(),
            Mock(),
        ]
        action.side_effect = actions

        with patch('gofer.agent.decorator.Actions.functions', dict(functions)):
            collated = Actions.collated()
            self.assertEqual(
                action.call_args_list,
                [
                    ((class_1().m1,), functions[0][1]),
                    ((class_1().m2,), functions[1][1]),
                    ((functions[2][0],), functions[2][1]),
                    ((functions[3][0],), functions[3][1]),
                ])
            self.assertEqual(collated, actions)


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
