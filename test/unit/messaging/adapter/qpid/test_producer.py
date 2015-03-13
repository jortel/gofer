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

from gofer.devel import ipatch

with ipatch('qpid'):
    from gofer.messaging.adapter.qpid.producer import BaseSender, Sender


class TestSender(TestCase):

    @patch('gofer.messaging.adapter.qpid.producer.Connection')
    def test_init(self, connection):
        url = 'test-url'

        # test
        sender = Sender(url)

        # validation
        connection.assert_called_once_with(url)
        self.assertTrue(isinstance(sender, BaseSender))
        self.assertEqual(sender.url, url)
        self.assertEqual(sender.connection, connection.return_value)
        self.assertEqual(sender.session, None)

    @patch('gofer.messaging.adapter.qpid.producer.Connection', Mock())
    def test_is_open(self):
        url = 'test-url'
        sender = Sender(url)
        # closed
        self.assertFalse(sender.is_open())
        # open
        sender.session = Mock()
        self.assertTrue(sender.is_open())

    @patch('gofer.messaging.adapter.qpid.producer.Connection')
    def test_open(self, connection):
        url = 'test-url'

        # test
        sender = Sender(url)
        sender.is_open = Mock(return_value=False)
        sender.open()

        # validation
        connection.return_value.open.assert_called_once_with()
        connection.return_value.session.assert_called_once_with()
        self.assertEqual(sender.session, connection.return_value.session.return_value)

    @patch('gofer.messaging.adapter.qpid.producer.Connection', Mock())
    def test_open_already(self):
        url = 'test-url'

        # test
        sender = Sender(url)
        sender.is_open = Mock(return_value=True)
        sender.open()

        # validation
        self.assertFalse(sender.connection.open.called)

    def test_close(self):
        connection = Mock()
        connection.opened.return_value = True
        session = Mock(connection=connection)

        # test
        sender = Sender(None)
        sender.connection = connection
        sender.session = session
        sender.is_open = Mock(return_value=True)
        sender.close()

        # validation
        session.close.assert_called_once_with()
        self.assertFalse(connection.close.called)

    def test_close_not_connected(self):
        connection = Mock()
        connection.opened.return_value = False
        session = Mock(connection=connection)

        # test
        sender = Sender(None)
        sender.connection = connection
        sender.session = session
        sender.is_open = Mock(return_value=True)
        sender.close()

        # validation
        self.assertFalse(session.close.called)
        self.assertFalse(connection.close.called)

    @patch('gofer.messaging.adapter.qpid.producer.Message')
    @patch('gofer.messaging.adapter.qpid.producer.Connection', Mock())
    def test_send(self, message):
        ttl = 10
        address = 'q1'
        content = 'hello'

        # test
        sender = Sender('')
        sender.durable = 18
        sender.session = Mock()
        sender.send(address, content, ttl=ttl)

        # validation
        message.assert_called_once_with(content=content, durable=sender.durable, ttl=ttl)
        sender.session.sender.assert_called_once_with(address)
        _sender = sender.session.sender.return_value
        _sender.send.assert_called_once_with(message.return_value)
        _sender.close.assert_called_once_with()
