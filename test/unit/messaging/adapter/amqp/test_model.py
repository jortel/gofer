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
    from gofer.messaging.adapter.amqp.model import EXPIRES


class FakeExchange(object):

    def __init__(self, name):
        self.name = name


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

    @patch('gofer.messaging.adapter.amqp.endpoint.Endpoint')
    def test_declare(self, endpoint):
        url = 'test-url'
        channel = Mock()
        endpoint.return_value.channel.return_value = channel

        # test
        exchange = Exchange('test', policy='direct')
        exchange.declare(url)

        # validation
        endpoint.channel.asssert_called_once_with()
        channel.exchange_declare.assert_called_once_with(
            exchange.name,
            exchange.policy,
            durable=exchange.durable,
            auto_delete=exchange.auto_delete,
            arguments=None)

    @patch('gofer.messaging.adapter.amqp.endpoint.Endpoint')
    def test_declare_auto_delete(self, endpoint):
        url = 'test-url'
        channel = Mock()
        endpoint.return_value.channel.return_value = channel

        # test
        exchange = Exchange('test', policy='direct')
        exchange.auto_delete = True
        exchange.declare(url)

        # validation
        endpoint.channel.asssert_called_once_with()
        channel.exchange_declare.assert_called_once_with(
            exchange.name,
            exchange.policy,
            durable=exchange.durable,
            auto_delete=exchange.auto_delete,
            arguments=EXPIRES)

    @patch('gofer.messaging.adapter.amqp.endpoint.Endpoint')
    def test_delete(self, endpoint):
        url = 'test-url'
        channel = Mock()
        endpoint.return_value.channel.return_value = channel

        # test
        exchange = Exchange('test')
        exchange.delete(url)

        # validation
        endpoint.channel.asssert_called_once_with()
        channel.exchange_delete.assert_called_once_with(exchange.name, nowait=True)


class TestQueue(TestCase):

    def test_init(self):
        name = 'test-queue'
        exchange = FakeExchange('direct')
        routing_key = 'routing-key'

        # test defaults
        queue = Queue(name)
        self.assertTrue(isinstance(queue, BaseQueue))
        self.assertTrue(queue.exchange, Exchange)
        self.assertEqual(queue.exchange.name, '')
        self.assertEqual(queue.routing_key, name)

        # test explicit
        queue = Queue(name, exchange, routing_key)
        self.assertTrue(isinstance(queue, BaseQueue))
        self.assertTrue(queue.exchange, exchange)
        self.assertEqual(queue.exchange.name, exchange.name)
        self.assertEqual(queue.routing_key, routing_key)

    @patch('gofer.messaging.adapter.amqp.endpoint.Endpoint')
    def test_declare(self, endpoint):
        url = 'test-url'
        channel = Mock()
        endpoint.return_value.channel.return_value = channel

        # test
        queue = Queue('test')
        queue.declare(url)

        # validation
        endpoint.channel.asssert_called_once_with()
        channel.queue_declare.assert_called_once_with(
            queue.name,
            durable=queue.durable,
            exclusive=queue.exclusive,
            auto_delete=queue.auto_delete,
            arguments=None)
        self.assertFalse(channel.queue_bind.called)

    @patch('gofer.messaging.adapter.amqp.endpoint.Endpoint')
    def test_declare_with_exchange(self, endpoint):
        url = 'test-url'
        channel = Mock()
        endpoint.return_value.channel.return_value = channel
        exchange = Mock(name='dog')

        # test
        queue = Queue('test', exchange=exchange)
        queue.declare(url)

        # validation
        endpoint.channel.asssert_called_once_with()
        channel.queue_declare.assert_called_once_with(
            queue.name,
            durable=queue.durable,
            exclusive=queue.exclusive,
            auto_delete=queue.auto_delete,
            arguments=None)
        channel.queue_bind.assert_called_once_with(
            queue.name,
            exchange=exchange.name,
            routing_key=queue.routing_key)

    @patch('gofer.messaging.adapter.amqp.endpoint.Endpoint')
    def test_declare_auto_delete(self, endpoint):
        url = 'test-url'
        channel = Mock()
        endpoint.return_value.channel.return_value = channel

        # test
        queue = Queue('test')
        queue.auto_delete = True
        queue.declare(url)

        # validation
        endpoint.channel.asssert_called_once_with()
        channel.queue_declare.assert_called_once_with(
            queue.name,
            durable=queue.durable,
            exclusive=queue.exclusive,
            auto_delete=queue.auto_delete,
            arguments=EXPIRES)

    @patch('gofer.messaging.adapter.amqp.endpoint.Endpoint')
    def test_delete(self, endpoint):
        url = 'test-url'
        channel = Mock()
        endpoint.return_value.channel.return_value = channel

        # test
        queue = Queue('test')
        queue.delete(url)

        # validation
        endpoint.channel.asssert_called_once_with()
        channel.queue_delete.assert_called_once_with(queue.name, nowait=True)

    @patch('gofer.messaging.adapter.amqp.model.Destination')
    def test_destination(self, destination):
        url = 'test-url'
        name = 'test-queue'

        # test
        queue = Queue(name)
        _destination = queue.destination(url)

        # validation
        destination.assert_called_once_with(
            routing_key=queue.routing_key, exchange=queue.exchange.name)
        self.assertEqual(_destination, destination.return_value)
