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

from gofer.compat import str
from gofer.devel import ipatch

with ipatch('qpid'):
    from gofer.messaging.adapter.qpid import model
    from gofer.messaging.adapter.qpid.model import Error, Method
    from gofer.messaging.adapter.qpid.model import Exchange, BaseExchange
    from gofer.messaging.adapter.qpid.model import Queue, BaseQueue


class TestError(TestCase):

    def test_init(self):
        code = 18
        description = '12345'
        error = Error(description, code)
        self.assertEqual(error.code, code)
        self.assertEqual(error.args[0], description)


class TestMethod(TestCase):

    @patch('gofer.messaging.adapter.qpid.model.Connection')
    def test_init(self, _connection):
        url = 'test-url'
        name = model.CREATE
        arguments = {'a': 1}
        method = Method(url, name, arguments)
        _connection.assert_called_once_with(url)
        self.assertEqual(method.url, url)
        self.assertEqual(method.name, name)
        self.assertEqual(method.arguments, arguments)
        self.assertEqual(method.connection, _connection.return_value)
        self.assertEqual(method.session, None)
        self.assertEqual(method.sender, None)
        self.assertEqual(method.receiver, None)

    def test_content(self):
        url = 'test-url'
        name = model.CREATE
        arguments = {'a': 1}
        method = Method(url, name, arguments)
        self.assertEqual(
            method.content,
            {
                '_object_id': model.OBJECT_ID,
                '_method_name': name,
                '_arguments': arguments
            })

    def test_properties(self):
        url = 'test-url'
        method = Method(url, model.CREATE, {})
        self.assertEqual(
            method.properties,
            {
                'qmf.opcode': '_method_request',
                'x-amqp-0-10.app-id': 'qmf2',
                'method': 'request'
            })

    def test_reply_succeeded(self):
        url = 'test-url'
        content = ''
        properties = {
            'qmf.opcode': ''
        }
        reply = Mock(content=content, properties=properties)
        method = Method(url, '', {})
        method.on_reply(reply)

    def test_reply_failed(self):
        url = 'test-url'
        values = {
            'error_code': 18,
            'error_text': 'just failed'
        }
        content = {'_values': values}
        properties = {
            'qmf.opcode': '_exception'
        }
        reply = Mock(content=content, properties=properties)
        method = Method(url, '', {})
        self.assertRaises(Error, method.on_reply, reply)

    def test_reply_already_exists(self):
        url = 'test-url'
        values = {
            'error_code': model.EEXIST,
            'error_text': 'just failed'
        }
        content = {'_values': values}
        properties = {
            'qmf.opcode': '_exception'
        }
        reply = Mock(content=content, properties=properties)
        method = Method(url, '', {})
        method.on_reply(reply)

    @patch('gofer.messaging.adapter.qpid.model.uuid4')
    @patch('gofer.messaging.adapter.qpid.model.Connection')
    def test_open(self, _connection, uuid):
        url = 'url-test'
        uuid.return_value = '5138'
        connection = Mock()
        _connection.return_value = connection
        session = Mock()
        session.close.side_effect = ValueError
        sender = Mock()
        sender.close.side_effect = ValueError
        receiver = Mock()
        receiver.close.side_effect = ValueError
        connection.session.return_value = session
        session.receiver.return_value = receiver
        session.sender.return_value = sender
        reply_to = model.REPLY_TO % uuid.return_value

        # test
        method = Method(url, '', {})
        method.open()

        # validation
        connection.open.assert_called_once_with()
        session.sender.assert_called_once_with(model.ADDRESS)
        session.receiver.assert_called_once_with(reply_to)
        self.assertEqual(method.connection, connection)
        self.assertEqual(method.sender, sender)
        self.assertEqual(method.receiver, receiver)

    @patch('gofer.messaging.adapter.qpid.model.Connection', Mock())
    def test_open_already(self):
        # test
        method = Method('', '', {})
        method.is_open = Mock(return_value=True)
        method.open()

        # validation
        self.assertFalse(method.connection.open.called)

    @patch('gofer.messaging.adapter.qpid.model.uuid4')
    @patch('gofer.messaging.adapter.qpid.model.Method.close')
    @patch('gofer.messaging.adapter.qpid.model.Connection')
    def test_repair(self, _connection, close, uuid):
        url = 'url-test'
        uuid.return_value = '5138'
        connection = Mock()
        _connection.return_value = connection
        session = Mock()
        session.close.side_effect = ValueError
        sender = Mock()
        sender.close.side_effect = ValueError
        receiver = Mock()
        receiver.close.side_effect = ValueError
        connection.session.return_value = session
        session.receiver.return_value = receiver
        session.sender.return_value = sender
        reply_to = model.REPLY_TO % uuid.return_value

        # test
        method = Method(url, '', {})
        method.repair()

        # validation
        close.assert_called_once_with()
        connection.close.assert_called_once_with()
        connection.open.assert_called_once_with()
        session.sender.assert_called_once_with(model.ADDRESS)
        session.receiver.assert_called_once_with(reply_to)
        self.assertEqual(method.connection, connection)
        self.assertEqual(method.sender, sender)
        self.assertEqual(method.receiver, receiver)

    def test_close(self):
        connection = Mock()
        session = Mock(connection=connection)
        sender = Mock()
        receiver = Mock()
        method = Method('', '', {})
        method.connection = connection
        method.session = session
        method.sender = sender
        method.receiver = receiver

        session.close.side_effect = ValueError
        sender.close.side_effect = ValueError
        receiver.close.side_effect = ValueError

        # test
        method.close()

        # validation
        receiver.close.assert_called_once_with()
        sender.close.assert_called_once_with()
        session.close.assert_called_once_with()
        self.assertFalse(connection.close.called)

    @patch('gofer.messaging.adapter.qpid.model.uuid4')
    @patch('gofer.messaging.adapter.qpid.model.Message')
    def test_call(self, message, uuid):
        url = 'url-test'
        name = model.CREATE
        arguments = {'a': 1}

        # test
        method = Method(url, name, arguments)
        method.reply_to = '234'
        method.open = Mock()
        method.close = Mock()
        method.session = Mock()
        method.sender = Mock()
        method.receiver = Mock()
        method.on_reply = Mock()
        method()

        # validation
        method.open.assert_called_once_with()
        message.assert_called_once_with(
            content=method.content,
            reply_to=method.reply_to,
            properties=method.properties,
            correlation_id=str(uuid.return_value).encode(),
            subject=model.SUBJECT
        )

        method.session.acknowledge.assert_called_once_with()
        method.sender.send.assert_called_once_with(message.return_value)
        method.on_reply.assert_called_once_with(method.receiver.fetch.return_value)
        method.close.assert_called_once_with()


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

    @patch('gofer.messaging.adapter.qpid.model.Method')
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

    @patch('gofer.messaging.adapter.qpid.model.Method')
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

    @patch('gofer.messaging.adapter.qpid.model.Method')
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

    @patch('gofer.messaging.adapter.qpid.model.Method')
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

    @patch('gofer.messaging.adapter.qpid.model.Method')
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

    @patch('gofer.messaging.adapter.qpid.model.Method')
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
