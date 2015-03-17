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

from gofer.agent.action import Action


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

    def test_unicode(self):
        action = Action(Mock(), hours=24)
        action.name = Mock(return_value='1234')

        # test
        s = unicode(action)

        # validation
        action.name.assert_called_once_with()
        self.assertEqual(s, action.name.return_value)

    def test_str(self):
        action = Action(Mock(), hours=24)
        action.name = Mock(return_value='1234')

        # test
        s = str(action)

        # validation
        action.name.assert_called_once_with()
        self.assertEqual(s, action.name.return_value)
