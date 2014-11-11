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

with ipatch('qpid.messaging'):
    from gofer.messaging.adapter.qpid.model import squash, Exchange, BaseExchange
    from gofer.messaging.adapter.qpid.model import Queue, BaseQueue
    from gofer.messaging.adapter.qpid.model import XBinding, XBindings


class FakeExchange(object):

    def __init__(self, name):
        self.name = name


class TestSquash(TestCase):

    def test_squash(self):
        json = '{ "name": "elmer",\n"age": 60}'
        squashed = squash(json)
        self.assertEqual(squashed, '{"name":"elmer","age":60}')


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

    def test_address(self):
        exchange = Exchange('test', policy='direct')
        address = exchange.address()
        self.assertEqual(
            address,
            squash("""
            test;{
              create:always,node:{
                type:topic,durable:True,
                x-declare:{
                  exchange:'test',type:direct
                }
              }
            }
            """))

    @patch('gofer.messaging.adapter.qpid.model.Endpoint')
    def test_declare(self, endpoint):
        url = 'test-url'
        sender = Mock()
        channel = Mock()
        channel.sender.return_value = sender
        address = 'test-address'
        endpoint.return_value.channel.return_value = channel

        # test
        exchange = Exchange('test', policy='direct')
        exchange.address = Mock(return_value=address)
        exchange.declare(url)

        # validation
        endpoint.assert_called_once_with(url)
        endpoint.channel.asssert_called_once_with()
        channel.sender.assert_called_once_with(address)
        sender.close.assert_called_once_with()

    @patch('gofer.messaging.adapter.qpid.model.Endpoint')
    def test_declare_no_policy(self, endpoint):
        exchange = Exchange('')
        exchange.declare('')
        self.assertFalse(endpoint.called)


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

    @patch('gofer.messaging.adapter.qpid.model.XBindings')
    @patch('gofer.messaging.adapter.qpid.model.XBinding')
    def test_bindings(self, x_binding, x_bindings):
        name = 'test-queue'

        # test
        queue = Queue(name, exchange=Exchange('direct'))
        bindings = queue.bindings()

        # validation
        x_binding.assert_called_once_with(queue.exchange, queue.routing_key)
        x_bindings.assert_called_once_with(x_binding.return_value)
        self.assertEqual(bindings, x_bindings.return_value)

    @patch('gofer.messaging.adapter.qpid.model.XBindings')
    def test_bindings_anonymous_exchange(self, x_bindings):
        name = 'test-queue'

        # test
        queue = Queue(name)
        bindings = queue.bindings()

        # validation
        x_bindings.assert_called_once_with()
        self.assertEqual(bindings, x_bindings.return_value)

    def test_x_declare(self):
        name = 'test-queue'

        # test
        queue = Queue(name)
        x_declare = queue.x_declare()

        # validation
        self.assertEqual(x_declare, '')

    def test_x_declare_auto_delete(self):
        name = 'test-queue'

        # test
        queue = Queue(name)
        queue.auto_delete = True
        x_declare = queue.x_declare()

        # validation
        self.assertEqual(
            x_declare,
            squash("""
                x-declare:{
                  auto-delete:True,
                  arguments:{
                    'qpid.auto_delete_timeout':10
                  }
                },
                """))

    def test_address(self):
        name = 'test-queue'

        # test
        queue = Queue(name)
        queue.durable = False
        address = queue.address()

        # validation
        self.assertEqual(
            address,
            squash("""
              test-queue;{
                create:always,
                delete:receiver,
                node:{
                  type:queue,
                  durable:False,
                },
                link:{
                  durable:True,
                  reliability:at-least-once,
                  x-subscribe:{
                    exclusive:False
                  }
                }
              }
            """))

    def test_exclusive_address(self):
        name = 'test-queue'

        # test
        queue = Queue(name)
        queue.durable = False
        queue.exclusive = True
        address = queue.address()

        # validation
        self.assertEqual(
            address,
            squash("""
              test-queue;{
                create:always,
                delete:receiver,
                node:{
                  type:queue,
                  durable:False,
                },
                link:{
                  durable:True,
                  reliability:at-least-once,
                  x-subscribe:{
                    exclusive:True
                  }
                }
              }
            """))

    def test_durable_address(self):
        name = 'test-queue'

        # test
        queue = Queue(name)
        queue.durable = True
        address = queue.address()

        # validation
        self.assertEqual(
            address,
            squash("""
              test-queue;{
                create:always,
                node:{
                  type:queue,
                  durable:True,
                },
                link:{
                  durable:True,
                  reliability:at-least-once,
                  x-subscribe:{
                    exclusive:False
                  }
                }
              }
            """))

    @patch('gofer.messaging.adapter.qpid.model.Endpoint')
    def test_declare(self, endpoint):
        url = 'test-url'
        sender = Mock()
        channel = Mock()
        channel.sender.return_value = sender
        address = 'test-address'
        endpoint.return_value.channel.return_value = channel

        # test
        queue = Queue('test')
        queue.address = Mock(return_value=address)
        queue.declare(url)

        # validation
        endpoint.assert_called_once_with(url)
        endpoint.channel.asssert_called_once_with()
        channel.sender.assert_called_once_with(address)
        sender.close.assert_called_once_with()

    @patch('gofer.messaging.adapter.qpid.model.Destination')
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

    @patch('gofer.messaging.adapter.qpid.model.Queue.address')
    def test_str(self, address):
        address.return_value = 'test-address'
        queue = Queue('')
        self.assertEqual(str(queue), address.return_value)



class TestXBinding(TestCase):

    def test_init(self):
        exchange = FakeExchange('test-exchange')
        routing_key = 'test-key'
        x_binding = XBinding(exchange, routing_key)
        self.assertEqual(x_binding.exchange, exchange.name)
        self.assertEqual(x_binding.routing_key, routing_key)

    def test_str(self):
        exchange = FakeExchange('test-exchange')
        routing_key = 'test-key'
        x_binding = XBinding(exchange)
        self.assertEqual(str(x_binding), "{exchange:'test-exchange'}")
        x_binding = XBinding(exchange, routing_key)
        self.assertEqual(str(x_binding), "{exchange:'test-exchange',key:'test-key'}")


class TestXBindings(TestCase):

    def test_init(self):
        bindings = (1, 2)
        x_bindings = XBindings(*bindings)
        self.assertEqual(x_bindings.bindings, bindings)

    def test_str(self):
        x_bindings = XBindings('A')
        self.assertEqual(str(x_bindings), 'x-bindings:[A]')
        x_bindings = XBindings('A', 'B')
        self.assertEqual(str(x_bindings), 'x-bindings:[A,B]')