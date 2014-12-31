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

from gofer.devel import ipatch

with ipatch('qpid'):
    from gofer.messaging.adapter.qpid.model import Broker
    from gofer.messaging.adapter.qpid.model import Exchange, BaseExchange
    from gofer.messaging.adapter.qpid.model import Queue, BaseQueue


class TestBroker(TestCase):

    @patch('gofer.messaging.adapter.qpid.model.Connection')
    def test_init(self, connection):
        url = 'test-url'

        # test
        broker = Broker(url)

        # validation
        connection.assert_called_once_with(url)
        connection.return_value.open.asssert_called_once_with()
        self.assertEqual(broker.args, (connection.return_value.impl,))
        self.assertEqual(broker._connection, connection.return_value)

    @patch('gofer.messaging.adapter.qpid.model.BrokerAgent')
    @patch('gofer.messaging.adapter.qpid.model.Connection')
    def test_close(self, connection, agent):
        url = 'test-url'

        # test
        broker = Broker(url)
        broker.close()

        # validation
        agent.close.assert_called_once_with(broker)
        connection.return_value.close.assert_called_once_with()

    @patch('gofer.messaging.adapter.qpid.model.Connection', Mock())
    def test_enter(self):
        url = 'test-url'
        broker = Broker(url)
        self.assertEqual(broker, broker.__enter__())

    @patch('gofer.messaging.adapter.qpid.model.Connection', Mock())
    def test_exit(self):
        url = 'test-url'
        broker = Broker(url)
        broker.close = Mock()
        broker.__exit__()
        broker.close.assert_called_once_with()


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

    @patch('gofer.messaging.adapter.qpid.model.Broker')
    def test_declare(self, broker):
        url = 'test-url'
        broker.return_value.getExchange.return_value = None

        # test
        exchange = Exchange('test', policy='direct')
        exchange.durable = 0
        exchange.auto_delete = 1
        exchange.declare(url)

        # validation
        options = {
            'durable': exchange.durable,
            'auto-delete': exchange.auto_delete
        }
        broker.assert_called_once_with(url)
        broker.return_value.addExchange.assert_called_once_with(exchange.policy, exchange.name, options)
        broker.return_value.close.assert_called_once_with()

    @patch('gofer.messaging.adapter.qpid.model.Broker')
    def test_declare_exists(self, broker):
        url = 'test-url'
        broker.return_value.addExchange.side_effect = Exception(': 7')

        # test
        exchange = Exchange('test', policy='direct')
        exchange.durable = 0
        exchange.auto_delete = 1
        exchange.declare(url)

        # validation
        options = {
            'durable': exchange.durable,
            'auto-delete': exchange.auto_delete
        }
        broker.assert_called_once_with(url)
        broker.return_value.addExchange.assert_called_once_with(exchange.policy, exchange.name, options)
        broker.return_value.close.assert_called_once_with()

    @patch('gofer.messaging.adapter.qpid.model.Broker')
    def test_delete(self, broker):
        url = 'test-url'
        broker.return_value.getExchange.return_value = None

        # test
        exchange = Exchange('test')
        exchange.delete(url)

        # validation
        broker.assert_called_once_with(url)
        broker.return_value.delExchange.assert_called_once_with(exchange.name)
        broker.return_value.close.assert_called_once_with()

    @patch('gofer.messaging.adapter.qpid.model.Broker')
    def test_bind(self, broker):
        url = 'test-url'
        queue = Queue('test-queue')

        # test
        exchange = Exchange('test-exchange')
        exchange.bind(queue, url)

        # validation
        broker.assert_called_once_with(url)
        broker.return_value.bind.assert_called_once_with(exchange.name, queue.name, queue.name)
        broker.return_value.close.assert_called_once_with()

    @patch('gofer.messaging.adapter.qpid.model.Broker')
    def test_unbind(self, broker):
        url = 'test-url'
        queue = Queue('test-queue')

        # test
        exchange = Exchange('test-exchange')
        exchange.unbind(queue, url)

        # validation
        broker.assert_called_once_with(url)
        broker.return_value.unbind.assert_called_once_with(exchange.name, queue.name, queue.name)
        broker.return_value.close.assert_called_once_with()


class TestQueue(TestCase):

    def test_init(self):
        name = 'test-queue'

        # test
        queue = Queue(name)

        # validation
        self.assertTrue(isinstance(queue, BaseQueue))
        self.assertEqual(queue.name, name)

    @patch('gofer.messaging.adapter.qpid.model.Broker')
    def test_declare(self, broker):
        url = 'test-url'
        name = 'test-queue'
        broker.return_value.getQueue.return_value = None

        # test
        queue = Queue(name)
        queue.durable = 0
        queue.auto_delete = 1
        queue.exclusive = 3
        queue.declare(url)

        # validation
        options = {
            'durable': queue.durable,
            'auto-delete': queue.auto_delete,
            'exclusive': queue.exclusive
        }
        broker.assert_called_once_with(url)
        broker.return_value.addQueue.assert_called_once_with(queue.name, options)
        broker.return_value.close.assert_called_once_with()

    @patch('gofer.messaging.adapter.qpid.model.Broker')
    def test_declare_exists(self, broker):
        url = 'test-url'
        name = 'test-queue'
        broker.return_value.addQueue.side_effect = Exception(': 7')

        # test
        queue = Queue(name)
        queue.durable = 0
        queue.auto_delete = 1
        queue.exclusive = 3
        queue.declare(url)

        # validation
        options = {
            'durable': queue.durable,
            'auto-delete': queue.auto_delete,
            'exclusive': queue.exclusive
        }
        broker.assert_called_once_with(url)
        broker.return_value.addQueue.assert_called_once_with(queue.name, options)
        broker.return_value.close.assert_called_once_with()

    @patch('gofer.messaging.adapter.qpid.model.Broker')
    def test_delete(self, broker):
        url = 'test-url'
        name = 'test-queue'

        # test
        queue = Queue(name)
        queue.delete(url)

        # validation
        broker.assert_called_once_with(url)
        broker.return_value.delQueue.assert_called_once_with(queue.name)
        broker.return_value.close.assert_called_once_with()
