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

with ipatch('proton'):
    from gofer.messaging.adapter.proton.producer import BaseSender, Sender, build_message


class TestBuilder(TestCase):

    @patch('gofer.messaging.adapter.proton.producer.Message')
    def test_build(self, message):
        content = Mock()
        ttl = None
        m = build_message(content, ttl)
        message.assert_called_once_with(body=content, durable=True)
        self.assertEqual(m, message.return_value)

    @patch('gofer.messaging.adapter.proton.producer.Message')
    def test_build_ttl(self, message):
        content = Mock()
        ttl = 10
        m = build_message(content, ttl)
        message.assert_called_once_with(body=content, durable=True, ttl=ttl)
        self.assertEqual(m, message.return_value)


class TestSender(TestCase):

    @patch('gofer.messaging.adapter.proton.producer.Connection')
    def test_init(self, connection):
        url = 'test-url'

        # test
        sender = Sender(url)

        # validation
        connection.assert_called_once_with(url)
        self.assertTrue(isinstance(sender, BaseSender))
        self.assertEqual(sender.url, url)
        self.assertEqual(sender.connection, connection.return_value)

    @patch('gofer.messaging.adapter.proton.producer.Connection', Mock())
    def test_is_open(self):
        url = 'test-url'
        sender = Sender(url)
        sender.connection = Mock()
        sender.connection.is_open.return_value = False
        # closed
        self.assertFalse(sender.is_open())
        # open
        sender.connection = Mock()
        sender.connection.is_open.return_value = True
        self.assertTrue(sender.is_open())

    @patch('gofer.messaging.adapter.proton.producer.Connection')
    def test_open(self, connection):
        url = 'test-url'

        # test
        sender = Sender(url)
        sender.is_open = Mock(return_value=False)
        sender.open()

        # validation
        connection.return_value.open.assert_called_once_with()

    @patch('gofer.messaging.adapter.proton.producer.Connection', Mock())
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
        connection.close.side_effect = ValueError

        # test
        sender = Sender(None)
        sender.connection = connection
        sender.is_open = Mock(return_value=True)
        sender.close()

        # validation
        self.assertFalse(connection.close.called)

    @patch('gofer.messaging.adapter.proton.producer.build_message')
    @patch('gofer.messaging.adapter.proton.producer.Connection', Mock())
    def test_send(self, builder):
        ttl = 10
        route = 'q1'
        content = 'hello'

        # test
        sender = Sender('')
        sender.connection = Mock()
        sender.send(route, content, ttl=ttl)

        # validation
        builder.assert_called_once_with(content, ttl)
        sender.connection.sender.assert_called_once_with(route)
        _sender = sender.connection.sender.return_value
        _sender.send.assert_called_once_with(builder.return_value)
        _sender.close.assert_called_once_with()
