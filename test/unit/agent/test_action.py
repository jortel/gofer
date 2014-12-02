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

from gofer.agent.action import Actions, Action, action


class TestActions(TestCase):

    def test_add(self):
        functions = {}
        fn = '<function>'
        interval = '<interval>'
        with patch('gofer.agent.action.Actions.functions', functions):
            Actions.add(fn, interval)
            self.assertEqual(functions, {fn: interval})

    def test_clear(self):
        functions = {}
        fn = '<function>'
        interval = '<interval>'
        with patch('gofer.agent.action.Actions.functions', functions):
            Actions.add(fn, interval)
            self.assertEqual(Actions.functions, {fn: interval})
            Actions.clear()
            self.assertEqual(Actions.functions, {})

    @patch('gofer.agent.action.Action')
    @patch('gofer.agent.action.Collator.collate')
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

        with patch('gofer.agent.action.Actions.functions', dict(functions)):
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

    @patch('gofer.agent.action.Actions.add')
    def test_decorator(self, add):
        fn = Mock()
        dfn = action(hours=10)
        dfn(fn)
        add.assert_called_once_with(fn, dict(hours=10))


class TestAction(TestCase):

    @patch('gofer.agent.action.dt')
    @patch('gofer.agent.action.timedelta')
    def test_init(self, delta, dt):
        target = Mock()
        interval = dict(hours=10)

        # test
        action = Action(target, **interval)

        # validation
        delta.assert_called_once_with(**interval)
        dt.assert_called_once_with(1900, 1, 1)
        self.assertEqual(action.target, target)
        self.assertEqual(action.interval, delta.return_value)
        self.assertEqual(action.last, dt.return_value)

    @patch('gofer.agent.action.inspect.ismethod')
    def test_name(self, is_method):
        # method
        is_method.return_value = True
        target = Mock(im_class='KL', __name__='bar')
        action = Action(target, hours=24)
        self.assertEqual(action.name(), 'KL.bar()')
        # function
        is_method.return_value = False
        target = Mock(__module__='MOD', __name__='bar')
        action = Action(target, hours=24)
        self.assertEqual(action.name(), 'MOD.bar()')

    @patch('gofer.agent.action.dt')
    @patch('gofer.agent.action.timedelta', Mock())
    def test_call(self, dt):
        now = 4
        dt.utcnow.return_value = now
        target = Mock()
        action = Action(target, seconds=10)
        action.last = 1
        action.interval = 2
        action.name = Mock(return_value='')

        # test
        action()

        # validation
        target.assert_called_once_with()
        self.assertEqual(action.last, now)

    @patch('gofer.agent.action.dt')
    @patch('gofer.agent.action.timedelta', Mock())
    def test_call_raised(self, dt):
        now = 4
        dt.utcnow.return_value = now
        target = Mock(side_effect=ValueError)
        action = Action(target, seconds=10)
        action.last = 1
        action.interval = 2
        action.name = Mock(return_value='')

        # test
        action()

        # validation
        target.assert_called_once_with()
        self.assertEqual(action.last, now)

    @patch('gofer.agent.action.dt')
    @patch('gofer.agent.action.timedelta', Mock())
    def test_not_called(self, dt):
        now = 3
        dt.utcnow.return_value = now
        target = Mock()
        action = Action(target, seconds=10)
        action.last = 1
        action.interval = 2

        # test
        action()

        # validation
        self.assertFalse(target.called)

    def test_str(self):
        action = Action(Mock(), hours=24)
        action.name = Mock(return_value='1234')

        # test
        s = str(action)

        # validation
        action.name.assert_called_once_with()
        self.assertEqual(s, action.name.return_value)
