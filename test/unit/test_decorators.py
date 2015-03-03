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
from gofer.decorators import options, remote, pam, user, action, load, unload, initializer


class Function(object):
    pass


class TestOptions(TestCase):

    def test_options(self):
        def fn(): pass
        opt = options(fn)
        self.assertEqual(str(opt), str({'security': []}))
        self.assertEqual(getattr(fn, NAME), opt)

    def test_options_already(self):
        def fn(): pass
        options(fn)
        opt = options(fn)
        self.assertEqual(str(opt), str({'security': []}))
        self.assertEqual(getattr(fn, NAME), opt)


class TestRemote(TestCase):

    @patch('gofer.decorators.Remote')
    def test_call(self, _remote):
        def fn(): pass
        remote(fn)
        opt = getattr(fn, NAME)
        self.assertEqual(str(opt), str({'security': []}))
        _remote.add.assert_called_once_with(fn)

    @patch('gofer.decorators.Remote')
    def test_secret(self, _remote):
        def fn(): pass
        secret = 'fedex'
        remote(secret)(fn)
        opt = getattr(fn, NAME)
        self.assertEqual(str(opt), str({'security': [('secret', {'secret': 'fedex'})]}))
        _remote.add.assert_called_once_with(fn)


class TestPam(TestCase):

    def test_call(self):
        def fn(): pass
        pam(user='root')(fn)
        opt = getattr(fn, NAME)
        self.assertEqual(
            str(opt),
            str({'security': [('pam', {'user': 'root', 'service': None})]}))

    def test_service(self):
        def fn(): pass
        pam(user='root', service='find')(fn)
        opt = getattr(fn, NAME)
        self.assertEqual(
            str(opt),
            str({'security': [('pam', {'user': 'root', 'service': 'find'})]}))


class TestUser(TestCase):

    def test_call(self):
        def fn(): pass
        user(name='root')(fn)
        opt = getattr(fn, NAME)
        self.assertEqual(
            str(opt),
            str({'security': [('pam', {'user': 'root', 'service': None})]}))


class TestAction(TestCase):

    @patch('gofer.decorators.Actions')
    def test_call(self, actions):
        def fn(): pass
        interval = dict(hours=10)
        action(**interval)(fn)
        actions.add.assert_called_once_with(fn, interval)


class TestLoading(TestCase):

    @patch('gofer.decorators.Loading')
    def test_load(self, loading):
        loading.plugin = Mock()
        def fn(): pass
        load(fn)
        loading.plugin.hook.init.append.assert_called_once_with(fn)

    @patch('gofer.decorators.Loading')
    def test_initializer(self, loading):
        loading.plugin = Mock()
        def fn(): pass
        initializer(fn)
        loading.plugin.hook.init.append.assert_called_once_with(fn)

    @patch('gofer.decorators.Loading')
    def test_unload(self, loading):
        loading.plugin = Mock()
        def fn(): pass
        unload(fn)
        loading.plugin.hook.unload.append.assert_called_once_with(fn)
