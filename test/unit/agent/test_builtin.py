
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

from gofer.agent.builtin import Admin, Builtin
from gofer.messaging import Document


class TestAdmin(TestCase):

    @patch('gofer.agent.builtin.Tracker')
    def test_cancel_sn(self, tracker):
        sn = '1234'
        admin = Admin()
        canceled = admin.cancel(sn=sn)
        tracker.return_value.cancel.assert_called_once_with(sn)
        self.assertEqual(canceled, [tracker.return_value.cancel.return_value])

    @patch('gofer.agent.builtin.Builder')
    @patch('gofer.agent.builtin.Tracker')
    def test_cancel_criteria(self, tracker, builder):
        sn = '1234'
        name = 'joe'
        criteria = {'eq': name}
        tracker.return_value.find.return_value = [sn]

        # test
        admin = Admin()
        canceled = admin.cancel(criteria=criteria)

        # validation
        builder.return_value.build.assert_called_once_with(criteria)
        tracker.return_value.cancel.assert_called_once_with(sn)
        self.assertEqual(canceled, [tracker.return_value.cancel.return_value])

    def test_hello(self):
        admin = Admin()
        self.assertEqual(admin.hello(), 'Hello, I am gofer agent')

    def test_echo(self):
        text = 'hello'
        admin = Admin()
        self.assertEqual(admin.echo(text), text)

    @patch('gofer.agent.builtin.Actions')
    @patch('gofer.agent.builtin.loaded')
    def test_help(self, loaded, actions):
        admin = Admin()
        admin.container = Mock()
        report = admin.help()
        loaded.assert_called_once_with(admin.container, actions.return_value)
        self.assertEqual(report, loaded.return_value)

    def test_call(self):
        admin = Admin()
        self.assertEqual(admin, admin())


class TestBuiltin(TestCase):

    def test__dispatcher(self):
        dispatcher = Builtin._dispatcher()
        self.assertTrue(Admin.__name__ in dispatcher.catalog)

    @patch('gofer.agent.builtin.Dispatcher')
    @patch('gofer.agent.builtin.ThreadPool')
    @patch('gofer.agent.builtin.Builtin._dispatcher', Mock())
    def test_init(self, pool, dispatcher):
        dispatcher.__iadd__ = Mock()
        plugin = Mock(container=Mock())
        builtin = Builtin(plugin)
        pool.assert_called_once_with(3)
        self.assertEqual(builtin.dispatcher, builtin._dispatcher.return_value)
        self.assertEqual(builtin.pool, pool.return_value)
        self.assertEqual(builtin.plugin, plugin)

    @patch('gofer.agent.builtin.ThreadPool', Mock())
    def test_properties(self):
        plugin = Mock(
            container=Mock(),
            authenticator=Mock(),
            url='http://1234')
        builtin = Builtin(plugin)
        self.assertEqual(builtin.url, builtin.url)
        self.assertEqual(builtin.authenticator, builtin.authenticator)

    @patch('gofer.agent.builtin.ThreadPool', Mock())
    def test_provides(self):
        name = 'Admin'
        plugin = Mock()
        builtin = Builtin(plugin)
        p = builtin.provides(name)
        self.assertTrue(p)

    def test_dispatch(self):
        request = Document(
            routing=['A', 'B'],
            request={
                'classname': 'Admin',
                'method': 'hello',
                'args': [],
                'keywords': {}
            })
        plugin = Mock()
        builtin = Builtin(plugin)
        result = builtin.dispatch(request)
        self.assertEqual(result.retval, Admin().hello())

    @patch('gofer.agent.builtin.ThreadPool')
    def test_start(self, pool):
        plugin = Mock(container=Mock())
        builtin = Builtin(plugin)
        builtin.start()
        pool.return_value.start.assert_called_once_with()

    @patch('gofer.agent.builtin.ThreadPool')
    def test_shutdown(self, pool):
        plugin = Mock(container=Mock())
        builtin = Builtin(plugin)
        builtin.shutdown()
        pool.return_value.shutdown.assert_called_once_with()
