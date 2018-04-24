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
    from gofer.messaging.adapter.amqp.model import Exchange, BaseExchange
    from gofer.messaging.adapter.amqp.model import Queue, BaseQueue


class TestExchange(TestCase):

    def test_init(self):
        name = 'test-exchange'
        policy = 'direct'

        # test
        exchange = Exchange(name, policy=policy)

        # validation
        self.assertTrue(isinstance(exchange, BaseExchange))
        self.assertEqual(exchange.name, name)
        self.assertEqual(exchange.policy, policy)
        self.assertEqual(exchange.auto_delete, False)

    @patch('gofer.messaging.adapter.amqp.reliability.Connection.channel')
    @patch('gofer.messaging.adapter.amqp.connection.RealConnection', Mock())
    def test_declare(self, channel):
        url = 'test-url'

        # test
        exchange = Exchange('test', policy='direct')
        exchange.declare(url)

        # validation
        channel.return_value.exchange_declare.assert_called_once_with(
            exchange.name,
            exchange.policy,
            durable=exchange.durable,
            auto_delete=exchange.auto_delete)

    @patch('gofer.messaging.adapter.amqp.reliability.Connection.channel')
    @patch('gofer.messaging.adapter.amqp.connection.RealConnection', Mock())
    def test_delete(self, channel):
        url = 'test-url'

        # test
        exchange = Exchange('test')
        exchange.delete(url)

        # validation
        channel.return_value.exchange_delete.assert_called_once_with(exchange.name, nowait=True)

    @patch('gofer.messaging.adapter.amqp.reliability.Connection.channel')
    @patch('gofer.messaging.adapter.amqp.connection.RealConnection', Mock())
    def test_bind(self, channel):
        url = 'test-url'
        queue = BaseQueue('test-queue')

        # test
        exchange = Exchange('test-exchange')
        exchange.bind(queue, url)

        # validation
        channel.return_value.queue_bind.assert_called_once_with(
            queue.name,
            exchange=exchange.name,
            routing_key=queue.name)

    @patch('gofer.messaging.adapter.amqp.reliability.Connection.channel')
    @patch('gofer.messaging.adapter.amqp.connection.RealConnection', Mock())
    def test_unbind(self, channel):
        url = 'test-url'
        queue = BaseQueue('test-queue')

        # test
        exchange = Exchange('test-exchange')
        exchange.unbind(queue, url)

        # validation
        channel.return_value.queue_unbind.assert_called_once_with(
            queue.name,
            exchange=exchange.name,
            routing_key=queue.name)


class TestQueue(TestCase):

    def test_init(self):
        name = 'test-queue'
        queue = Queue(name)
        self.assertEqual(queue.name, name)
        self.assertTrue(isinstance(queue, BaseQueue))
        self.assertEqual(queue.exclusive, False)
        self.assertEqual(queue.auto_delete, False)
        self.assertEqual(queue.expiration, 0)

    @patch('gofer.messaging.adapter.amqp.reliability.Connection.channel')
    @patch('gofer.messaging.adapter.amqp.connection.RealConnection', Mock())
    def test_declare(self, channel):
        url = 'test-url'

        # test
        queue = Queue('test')
        queue.declare(url)

        # validation
        channel.return_value.queue_declare.assert_called_once_with(
            queue.name,
            durable=queue.durable,
            exclusive=queue.exclusive,
            auto_delete=queue.auto_delete,
            arguments=None)

    @patch('gofer.messaging.adapter.amqp.reliability.Connection.channel')
    @patch('gofer.messaging.adapter.amqp.connection.RealConnection', Mock())
    def test_declare_auto_delete(self, channel):
        url = 'test-url'

        # test
        queue = Queue('test')
        queue.auto_delete = True
        queue.expiration = 10
        queue.declare(url)

        # validation
        channel.return_value.queue_declare.assert_called_once_with(
            queue.name,
            durable=queue.durable,
            exclusive=queue.exclusive,
            auto_delete=queue.auto_delete,
            arguments={'x-expires': queue.expiration * 1000})

    @patch('gofer.messaging.adapter.amqp.reliability.Connection.channel')
    @patch('gofer.messaging.adapter.amqp.connection.RealConnection', Mock())
    def test_delete(self, channel):
        url = 'test-url'

        # test
        queue = Queue('test')
        queue.delete(url)

        # validation
        channel.return_value.queue_delete.assert_called_once_with(queue.name, nowait=True)
