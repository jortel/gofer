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

with ipatch('amqplib'):
    from gofer.messaging.adapter.amqplib.model import Exchange, BaseExchange
    from gofer.messaging.adapter.amqplib.model import Queue, BaseQueue
    from gofer.messaging.adapter.amqplib.model import EXPIRES


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

    @patch('gofer.messaging.adapter.amqplib.endpoint.Endpoint')
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

    @patch('gofer.messaging.adapter.amqplib.endpoint.Endpoint')
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

    @patch('gofer.messaging.adapter.amqplib.endpoint.Endpoint')
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

    @patch('gofer.messaging.adapter.amqplib.endpoint.Endpoint')
    def test_bind(self, endpoint):
        url = 'test-url'
        channel = Mock()
        queue = BaseQueue('test-queue')
        endpoint.return_value.channel.return_value = channel

        # test
        exchange = Exchange('test-exchange')
        exchange.bind(queue, url)

        # validation
        endpoint.channel.asssert_called_once_with()
        channel.queue_bind.assert_called_once_with(
            queue.name,
            exchange=exchange.name,
            routing_key=queue.name)

    @patch('gofer.messaging.adapter.amqplib.endpoint.Endpoint')
    def test_unbind(self, endpoint):
        url = 'test-url'
        channel = Mock()
        queue = BaseQueue('test-queue')
        endpoint.return_value.channel.return_value = channel

        # test
        exchange = Exchange('test-exchange')
        exchange.unbind(queue, url)

        # validation
        endpoint.channel.asssert_called_once_with()
        channel.queue_unbind.assert_called_once_with(
            queue.name,
            exchange=exchange.name,
            routing_key=queue.name)


class TestQueue(TestCase):

    def test_init(self):
        name = 'test-queue'
        queue = Queue(name)
        self.assertEqual(queue.name, name)
        self.assertTrue(isinstance(queue, BaseQueue))

    @patch('gofer.messaging.adapter.amqplib.endpoint.Endpoint')
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

    @patch('gofer.messaging.adapter.amqplib.endpoint.Endpoint')
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

    @patch('gofer.messaging.adapter.amqplib.endpoint.Endpoint')
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
