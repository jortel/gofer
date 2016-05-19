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

from mock import patch, Mock

from gofer import NAME
from gofer.decorators import options, remote, pam, user, action
from gofer.decorators import load, unload, initializer
from gofer.decorators import DIRECT


class Function(object):
    pass


class TestOptions(TestCase):

    def test_options(self):
        def fn(): pass
        opt = options(fn)
        self.assertEqual(
            str(opt),
            str({
                'security': [],
                'call': {'model': DIRECT}
                }))
        self.assertEqual(getattr(fn, NAME), opt)

    def test_options_already(self):
        def fn(): pass
        options(fn)
        opt = options(fn)
        self.assertEqual(
            str(opt),
            str({
                'security': [],
                'call': {'model': DIRECT}
                }))
        self.assertEqual(getattr(fn, NAME), opt)


class TestRemote(TestCase):

    @patch('gofer.decorators.Remote')
    def test_call(self, _remote):
        def fn(): pass
        remote(fn)
        opt = getattr(fn, NAME)
        self.assertEqual(
            str(opt),
            str({
                'security': [],
                'call': {'model': DIRECT}
                }))
        _remote.add.assert_called_once_with(fn)

    @patch('gofer.decorators.Remote')
    def test_secret(self, _remote):
        def fn(): pass
        secret = 'fedex'
        remote(secret=secret)(fn)
        opt = getattr(fn, NAME)
        self.assertEqual(
            str(opt),
            str({
                'security': [
                    ('secret', {'secret': 'fedex'})
                ],
                'call': {'model': DIRECT}
                }))
        _remote.add.assert_called_once_with(fn)


class TestPam(TestCase):

    def test_call(self):
        def fn(): pass
        pam(user='root')(fn)
        opt = getattr(fn, NAME)
        self.assertEqual(
            str(opt),
            str({
                'security': [
                    ('pam', {'user': 'root', 'service': None})
                ],
                'call': {'model': DIRECT}
                }))

    def test_service(self):
        def fn(): pass
        pam(user='root', service='find')(fn)
        opt = getattr(fn, NAME)
        self.assertEqual(
            str(opt),
            str({
                'security': [
                    ('pam', {'user': 'root', 'service': 'find'})
                ],
                'call': {'model': DIRECT}
                }))


class TestUser(TestCase):

    def test_call(self):
        def fn(): pass
        user(name='root')(fn)
        opt = getattr(fn, NAME)
        self.assertEqual(
            str(opt),
            str({
                'security': [
                    ('pam', {'user': 'root', 'service': None})
                ],
                'call': {'model': DIRECT}
                }))


class TestAction(TestCase):

    @patch('gofer.decorators.Actions')
    def test_recurring(self, actions):
        def fn(): pass
        interval = dict(hours=10)
        action(**interval)(fn)
        actions.add.assert_called_once_with(fn, interval)

    @patch('gofer.decorators.Actions')
    def test_single(self, actions):
        def fn(): pass
        action(fn)
        actions.add.assert_called_once_with(fn, {'days': 36500})


class TestDelegate(TestCase):

    @patch('gofer.decorators.Delegate')
    def test_load(self, delegate):
        fn = Mock()
        delegate.load = Mock()
        load(fn)
        delegate.load.append.assert_called_once_with(fn)

    @patch('gofer.decorators.Delegate')
    def test_initializer(self, delegate):
        fn = Mock()
        delegate.load = Mock()
        initializer(fn)
        delegate.load.append.assert_called_once_with(fn)

    @patch('gofer.decorators.Delegate')
    def test_unload(self, delegate):
        fn = Mock()
        delegate.unload = Mock()
        unload(fn)
        delegate.unload.append.assert_called_once_with(fn)
