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

with ipatch('amqp'):
    from gofer.messaging.adapter.amqp.producer import build_message
    from gofer.messaging.adapter.amqp.producer import Sender, BaseSender


class TestBuildMessage(TestCase):

    @patch('gofer.messaging.adapter.amqp.producer.Message')
    def test_call(self, message):
        ttl = 10
        durable = False
        body = 'test-body'

        # test
        m = build_message(body, ttl, durable)

        # validation
        message.assert_called_once_with(body, delivery_mode=1, expiration=str(ttl * 1000))
        self.assertEqual(m, message.return_value)

    @patch('gofer.messaging.adapter.amqp.producer.Message')
    def test_call_durable(self, message):
        ttl = 10
        durable = True
        body = 'test-body'

        # test
        m = build_message(body, ttl, durable)

        # validation
        message.assert_called_once_with(body, delivery_mode=2, expiration=str(ttl * 1000))
        self.assertEqual(m, message.return_value)

    @patch('gofer.messaging.adapter.amqp.producer.Message')
    def test_call_no_ttl(self, message):
        ttl = 0
        body = 'test-body'
        durable = True

        # test
        m = build_message(body, ttl, durable)

        # validation
        message.assert_called_once_with(body, delivery_mode=2)
        self.assertEqual(m, message.return_value)


class TestSender(TestCase):

    @patch('gofer.messaging.adapter.amqp.producer.Connection')
    def test_init(self, connection):
        url = 'test-url'

        # test
        sender = Sender(url)

        # validation
        connection.assert_called_once_with(url)
        self.assertTrue(isinstance(sender, BaseSender))
        self.assertEqual(sender.url, url)
        self.assertEqual(sender.connection, connection.return_value)
        self.assertEqual(sender.channel, None)

    @patch('gofer.messaging.adapter.amqp.producer.Connection', Mock())
    def test_is_open(self):
        url = 'test-url'
        sender = Sender(url)
        # closed
        self.assertFalse(sender.is_open())
        # open
        sender.channel = Mock()
        self.assertTrue(sender.is_open())

    @patch('gofer.messaging.adapter.amqp.producer.Connection')
    def test_open(self, connection):
        url = 'test-url'

        # test
        sender = Sender(url)
        sender.is_open = Mock(return_value=False)
        sender.open()

        # validation
        connection.return_value.open.assert_called_once_with()
        connection.return_value.channel.assert_called_once_with()
        self.assertEqual(sender.channel, connection.return_value.channel.return_value)

    @patch('gofer.messaging.adapter.amqp.producer.Connection')
    def test_repair(self, connection):
        url = 'test-url'

        # test
        sender = Sender(url)
        sender.close = Mock()
        sender.repair()

        # validation
        sender.close.assert_called_once_with()
        sender.connection.close.assert_called_once_with()
        connection.return_value.open.assert_called_once_with()
        connection.return_value.channel.assert_called_once_with()
        self.assertEqual(sender.channel, connection.return_value.channel.return_value)

    @patch('gofer.messaging.adapter.amqp.producer.Connection', Mock())
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
        channel = Mock()
        # test
        sender = Sender(None)
        sender.connection = connection
        sender.channel = channel
        sender.is_open = Mock(return_value=True)
        sender.close()

        # validation
        channel.close.assert_called_once_with()
        self.assertFalse(connection.close.called)

    @patch('gofer.messaging.adapter.amqp.producer.build_message')
    @patch('gofer.messaging.adapter.amqp.producer.Connection', Mock())
    def test_send(self, build):
        ttl = 10
        address = 'jeff'
        content = 'hello'

        # test
        sender = Sender('')
        sender.durable = 18
        sender.channel = Mock()
        sender.send(address, content, ttl=ttl)

        # validation
        build.assert_called_once_with(content, ttl, sender.durable)
        sender.channel.basic_publish.assert_called_once_with(
            build.return_value,
            mandatory=True,
            exchange='',
            routing_key='jeff')


    @patch('gofer.messaging.adapter.amqp.producer.build_message')
    @patch('gofer.messaging.adapter.amqp.producer.Connection', Mock())
    def test_send_exchange(self, build):
        ttl = 10
        exchange = 'amq.direct'
        key = 'bar'
        address = '/'.join((exchange, key))
        content = 'hello'

        # test
        sender = Sender('')
        sender.durable = False
        sender.channel = Mock()
        sender.send(address, content, ttl=ttl)

        # validation
        build.assert_called_once_with(content, ttl, sender.durable)
        sender.channel.basic_publish.assert_called_once_with(
            build.return_value,
            mandatory=True,
            exchange=exchange,
            routing_key=key)
