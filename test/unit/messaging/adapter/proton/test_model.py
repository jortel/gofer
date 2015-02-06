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

with ipatch('proton'):
    from gofer.messaging.adapter.proton import model
    from gofer.messaging.adapter.proton.model import Error, Method
    from gofer.messaging.adapter.proton.model import Exchange, BaseExchange
    from gofer.messaging.adapter.proton.model import Queue, BaseQueue


class TestError(TestCase):

    def test_init(self):
        code = 18
        description = '12345'
        error = Error(description, code)
        self.assertEqual(error.code, code)
        self.assertEqual(error.args[0], description)


class TestMethod(TestCase):

    def test_init(self):
        url = 'test-url'
        name = model.CREATE
        arguments = {'a': 1}
        method = Method(url, name, arguments)
        self.assertEqual(method.url, url)
        self.assertEqual(method.name, name)
        self.assertEqual(method.arguments, arguments)

    def test_body(self):
        name = model.CREATE
        arguments = {'a': 1}
        method = Method('', name, arguments)
        self.assertEqual(
            method.body,
            {
                '_object_id': model.OBJECT_ID,
                '_method_name': name,
                '_arguments': arguments
            })

    def test_properties(self):
        method = Method('', model.CREATE, {})
        self.assertEqual(
            method.properties,
            {
                'qmf.opcode': '_method_request',
                'x-amqp-0-10.app-id': 'qmf2',
                'method': 'request'
            })

    def test_send(self):
        request = Mock()
        method = Method('', '', {})
        method.sender = Mock()
        method.send(request)
        method.sender.send.assert_called_with(request)

    def test_reply_succeeded(self):
        body = ''
        properties = {
            'qmf.opcode': ''
        }
        reply = Mock(body=body, properties=properties)
        method = Method('', '', {})
        method.on_reply(reply)

    def test_reply_failed(self):
        values = {
            'error_code': 18,
            'error_text': 'just failed'
        }
        body = {'_values': values}
        properties = {
            'qmf.opcode': '_exception'
        }
        reply = Mock(body=body, properties=properties)
        method = Method('', '', {})
        self.assertRaises(Error, method.on_reply, reply)

    def test_reply_already_exists(self):
        values = {
            'error_code': model.EEXIST,
            'error_text': 'just failed'
        }
        body = {'_values': values}
        properties = {
            'qmf.opcode': '_exception'
        }
        reply = Mock(body=body, properties=properties)
        method = Method('', '', {})
        method.on_reply(reply)

    @patch('gofer.messaging.adapter.proton.model.uuid4')
    @patch('gofer.messaging.adapter.proton.model.Connection')
    def test_open(self, _connection, uuid):
        url = 'url-test'
        uuid.return_value = '5138'
        connection = Mock()
        _connection.return_value = connection
        sender = Mock()
        sender.close.side_effect = ValueError
        receiver = Mock()
        receiver.close.side_effect = ValueError
        connection.receiver.return_value = receiver
        connection.sender.return_value = sender

        # test
        method = Method(url, '', {})
        method.open()

        # validation
        _connection.assert_called_once_with(url)
        connection.open.assert_called_once_with()
        connection.sender.assert_called_once_with(model.ADDRESS)
        connection.receiver.assert_called_once_with(model.ADDRESS, dynamic=True)
        self.assertEqual(method.connection, connection)
        self.assertEqual(method.sender, sender)
        self.assertEqual(method.receiver, receiver)

    def test_close(self):
        connection = Mock()
        sender = Mock()
        receiver = Mock()
        method = Method('', '', {})
        method.connection = connection
        method.sender = sender
        method.receiver = receiver

        # test
        method.close()

        # validation
        receiver.close.assert_called_once_with()
        sender.close.assert_called_once_with()

    @patch('gofer.messaging.adapter.proton.model.uuid4')
    @patch('gofer.messaging.adapter.proton.model.Message')
    @patch('gofer.messaging.adapter.proton.model.Connection')
    def test_call(self, _connection, message, uuid):
        url = 'url-test'
        name = model.CREATE
        arguments = {'a': 1}
        uuid.return_value = '5138'
        connection = Mock()
        _connection.return_value = connection
        sender = Mock()
        sender.close.side_effect = ValueError
        receiver = Mock()
        receiver.close.side_effect = ValueError
        connection.receiver.return_value = receiver
        connection.sender.return_value = sender

        # test
        method = Method(url, name, arguments)
        method.on_reply = Mock()
        method()

        # validation
        _connection.assert_called_once_with(url)
        connection.open.assert_called_once_with()

        connection.sender.assert_called_once_with(model.ADDRESS)
        connection.receiver.assert_called_once_with(model.ADDRESS, dynamic=True)

        message.assert_called_once_with(
            body=method.body,
            reply_to=receiver.remote_source.address,
            properties=method.properties,
            correlation_id=str(uuid.return_value),
            subject=model.SUBJECT
        )

        sender.send.assert_called_once_with(message.return_value)
        method.on_reply.assert_called_once_with(receiver.receive.return_value)
        sender.close.assert_called_once_with()
        receiver.close.assert_called_once_with()


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

    @patch('gofer.messaging.adapter.proton.model.Method')
    def test_declare(self, method):
        url = 'test-url'

        # test
        exchange = Exchange('test', policy='direct')
        exchange.durable = 0
        exchange.auto_delete = 1
        exchange.declare(url)

        # validation
        arguments = {
            'strict': True,
            'name': exchange.name,
            'type': 'exchange',
            'exchange-type': exchange.policy,
            'properties': {
                'auto-delete': exchange.auto_delete,
                'durable': exchange.durable
            }
        }
        method.assert_called_once_with(url, model.CREATE, arguments)
        method.return_value.assert_called_once_with()

    @patch('gofer.messaging.adapter.proton.model.Method')
    def test_delete(self, method):
        url = 'test-url'

        # test
        exchange = Exchange('test')
        exchange.delete(url)

        # validation
        arguments = {
            'strict': True,
            'name': exchange.name,
            'type': 'exchange',
            'properties': {}
        }
        method.assert_called_once_with(url, model.DELETE, arguments)
        method.return_value.assert_called_once_with()

    @patch('gofer.messaging.adapter.proton.model.Method')
    def test_bind(self, method):
        url = 'test-url'
        queue = Queue('test-queue')

        # test
        exchange = Exchange('test')
        exchange.bind(queue, url)

        # validation
        arguments = {
            'strict': True,
            'name': '/'.join((exchange.name, queue.name, queue.name)),
            'type': 'binding',
            'properties': {}
        }
        method.assert_called_once_with(url, model.CREATE, arguments)
        method.return_value.assert_called_once_with()

    @patch('gofer.messaging.adapter.proton.model.Method')
    def test_unbind(self, method):
        url = 'test-url'
        queue = Queue('test-queue')

        # test
        exchange = Exchange('test')
        exchange.unbind(queue, url)

        # validation
        arguments = {
            'strict': True,
            'name': '/'.join((exchange.name, queue.name, queue.name)),
            'type': 'binding',
            'properties': {}
        }
        method.assert_called_once_with(url, model.DELETE, arguments)
        method.return_value.assert_called_once_with()


class TestQueue(TestCase):

    def test_init(self):
        name = 'test-queue'

        # test
        queue = Queue(name)

        # validation
        self.assertTrue(isinstance(queue, BaseQueue))
        self.assertEqual(queue.name, name)

    @patch('gofer.messaging.adapter.proton.model.Method')
    def test_declare(self, method):
        url = 'test-url'

        # test
        queue = Queue('test-queue')
        queue.durable = 0
        queue.auto_delete = True
        queue.expiration = 10
        queue.exclusive = 3
        queue.declare(url)

        # validation
        arguments = {
            'strict': True,
            'name': queue.name,
            'type': 'queue',
            'properties': {
                'exclusive': queue.exclusive,
                'auto-delete': queue.auto_delete,
                'durable': queue.durable
            }
        }
        method.assert_called_once_with(url, model.CREATE, arguments)
        method.return_value.assert_called_once_with()

    @patch('gofer.messaging.adapter.proton.model.Method')
    def test_delete(self, method):
        url = 'test-url'

        # test
        queue = Queue('test-queue')
        queue.delete(url)

        # validation
        arguments = {
            'strict': True,
            'name': queue.name,
            'type': 'queue',
            'properties': {}
        }
        method.assert_called_once_with(url, model.DELETE, arguments)
        method.return_value.assert_called_once_with()
