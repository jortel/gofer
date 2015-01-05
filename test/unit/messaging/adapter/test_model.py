#
# Copyright (c) 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU Lesser General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (LGPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of LGPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/lgpl-2.0.txt.
#
# Jeff Ortel <jortel@redhat.com>
#

from unittest import TestCase

from mock import patch, Mock

from gofer.messaging.model import Document, VERSION
from gofer.messaging.adapter.url import URL
from gofer.messaging.adapter.model import Model, _Domain, Node
from gofer.messaging.adapter.model import BaseExchange, Exchange, DIRECT
from gofer.messaging.adapter.model import BaseQueue, Queue
from gofer.messaging.adapter.model import BaseEndpoint, Messenger
from gofer.messaging.adapter.model import BaseReader, Reader
from gofer.messaging.adapter.model import BaseSender, Sender, Producer
from gofer.messaging.adapter.model import Broker, SSL
from gofer.messaging.adapter.model import BaseConnection, Connection, SharedConnection
from gofer.messaging.adapter.model import Message
from gofer.messaging.adapter.model import ModelError
from gofer.messaging.adapter.model import model, blocking, DELAY, DELAY_MULTIPLIER


TEST_URL = 'qpid+amqp://elmer:fudd@test.com/test'


class Local(object):
    pass


class FakeConnection(object):

    __metaclass__ = SharedConnection

    def __init__(self, url):
        self.url = url


class TestModelDecorator(TestCase):

    def test_call(self):
        fn = Mock()
        _fn = model(fn)
        args = [1, 2, 3]
        keywords = dict(a=1, b=2)
        ret = _fn(*args, **keywords)
        fn.assert_called_once_with(*args, **keywords)
        self.assertEqual(ret, fn.return_value)

    def test_raised_model_error(self):
        fn = Mock(side_effect=ModelError)
        _fn = model(fn)
        self.assertRaises(ModelError, _fn)

    def test_raised_other(self):
        fn = Mock(side_effect=ValueError)
        _fn = model(fn)
        self.assertRaises(ModelError, _fn)


class TestBlockingDecorator(TestCase):

    def test_call(self):
        fn = Mock()
        _fn = blocking(fn)
        reader = Mock()
        timeout = 10
        message = _fn(reader, timeout)
        fn.assert_called_once_with(reader, timeout)
        self.assertEqual(message, fn.return_value)

    @patch('gofer.messaging.adapter.model.sleep')
    def test_delay(self, sleep):
        received = [
            None,
            None,
            Mock()]
        fn = Mock(side_effect=received)
        _fn = blocking(fn)
        reader = Mock()
        timeout = 10
        message = _fn(reader, timeout)
        self.assertEqual(
            fn.call_args_list,
            [
                ((reader, float(timeout)), {}),
                ((reader, float(timeout - DELAY)), {}),
                ((reader, float(timeout - (DELAY + (DELAY * DELAY_MULTIPLIER)))), {})
            ])
        self.assertEqual(
            sleep.call_args_list,
            [
                ((DELAY,), {}),
                ((DELAY * DELAY_MULTIPLIER,), {})
            ])
        self.assertEqual(message, received[-1])

    @patch('gofer.messaging.adapter.model.sleep')
    def test_call_blocking(self, sleep):
        fn = Mock(return_value=None)
        _fn = blocking(fn)
        reader = Mock()
        timeout = 10
        message = _fn(reader, timeout)
        self.assertEqual(message, None)
        total = 0.0
        for call in sleep.call_args_list:
            total += call[0][0]
        self.assertEqual(int(total), timeout)
        self.assertEqual(fn.call_count, 43)


class TestModel(TestCase):

    def test_domain_id(self):
        model = Model()
        self.assertEqual(model.domain_id, '::'.join((model.__class__.__name__, str(id(model)))))


class TestDomain(TestCase):

    def test_init(self):
        builder = Mock()
        domain = _Domain(builder)
        self.assertEqual(domain.builder, builder)
        self.assertEqual(domain.content, {})

    def test_all(self):
        cat = Node('cat')
        dog = Queue('dog')
        builder = Mock()
        domain = _Domain(builder)
        domain.add(cat)
        # add
        domain.add(dog)
        self.assertEqual(domain.content, {'Node::cat': cat, 'Queue::dog': dog})
        # contains
        self.assertTrue(domain.contains(dog))
        self.assertFalse(domain.contains(Node('dog')))
        self.assertTrue(dog in domain)
        # find
        self.assertEqual(domain.find(dog.domain_id), dog)
        # find (with builder)
        self.assertEqual(domain.find('123'), builder.return_value)
        builder.assert_called_once_with('123')
        # len
        self.assertEqual(len(domain), 2)
        # delete
        domain.delete(dog)
        self.assertEqual(domain.content, {'Node::cat': cat})


class TestNode(TestCase):

    def test_init(self):
        name = 'test'
        n = Node(name)
        self.assertEqual(n.name, name)

    def test_abstract(self):
        n = Node('test')
        self.assertRaises(NotImplementedError, n.declare, '')
        self.assertRaises(NotImplementedError, n.delete, '')

    def test_domain_id(self):
        n = Node('test')
        self.assertEqual(n.domain_id, 'Node::test')


class TestBaseExchange(TestCase):

    def test_init(self):
        name = 'test'
        exchange = BaseExchange(name)
        self.assertEqual(exchange.name, name)
        self.assertEqual(exchange.policy, DIRECT)
        # with policy
        policy = 'direct'
        exchange = BaseExchange(name, policy=policy)
        self.assertEqual(exchange.name, name)
        self.assertEqual(exchange.policy, policy)

    def test_abstract(self):
        exchange = BaseExchange('')
        self.assertRaises(NotImplementedError, exchange.bind, '', '')
        self.assertRaises(NotImplementedError, exchange.unbind, '', '')

    def test_eq(self):
        self.assertTrue(Exchange('1') == Exchange('1'))
        self.assertFalse(Exchange('1') == Exchange('2'))

    def test_neq(self):
        self.assertTrue(Exchange('1') != Exchange('2'))
        self.assertFalse(Exchange('1') != Exchange('1'))


class TestExchange(TestCase):

    def test_init(self):
        name = 'test'
        exchange = BaseExchange(name)
        self.assertEqual(exchange.name, name)
        self.assertEqual(exchange.policy, DIRECT)
        # with policy
        policy = 'direct'
        exchange = BaseExchange(name, policy=policy)
        self.assertEqual(exchange.name, name)
        self.assertEqual(exchange.policy, policy)

    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_declare(self, _find):
        plugin = Mock()
        _find.return_value = plugin
        exchange = Exchange('test')
        exchange.durable = 1
        exchange.auto_delete = 2

        # test
        exchange.declare(TEST_URL)

        # validation
        plugin.Exchange.assert_called_with(exchange.name, exchange.policy)
        impl = plugin.Exchange()
        impl.declare.assert_called_with(TEST_URL)
        self.assertEqual(impl.durable, exchange.durable)
        self.assertEqual(impl.auto_delete, exchange.auto_delete)

    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_delete(self, _find):
        plugin = Mock()
        _find.return_value = plugin
        exchange = Exchange('test')

        # test
        exchange.delete(TEST_URL)

        # validation
        plugin.Exchange.assert_called_with(exchange.name, exchange.policy)
        impl = plugin.Exchange()
        impl.delete.assert_called_with(TEST_URL)

    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_bind(self, _find):
        plugin = Mock()
        _find.return_value = plugin
        queue = Mock()

        # test
        exchange = Exchange('test')
        exchange.bind(queue, TEST_URL)

        # validation
        plugin.Exchange.assert_called_with(exchange.name, exchange.policy)
        impl = plugin.Exchange()
        impl.bind.assert_called_with(queue, TEST_URL)

    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_unbind(self, _find):
        plugin = Mock()
        _find.return_value = plugin
        queue = Mock()

        # test
        exchange = Exchange('test')
        exchange.unbind(queue, TEST_URL)

        # validation
        plugin.Exchange.assert_called_with(exchange.name, exchange.policy)
        impl = plugin.Exchange()
        impl.unbind.assert_called_with(queue, TEST_URL)


class TestBaseQueue(TestCase):

    def test_init(self):
        name = 'test'
        queue = BaseQueue(name)
        self.assertEqual(queue.name, name)

    def test_eq(self):
        self.assertTrue(BaseQueue('1') == BaseQueue('1'))
        self.assertFalse(BaseQueue('1') == BaseQueue('2'))

    def test_neq(self):
        self.assertTrue(BaseQueue('1') != BaseQueue('2'))
        self.assertFalse(BaseQueue('1') != BaseQueue('1'))


class TestQueue(TestCase):

    def test_init(self):
        name = 'test'
        queue = Queue(name)
        self.assertEqual(queue.name, name)

    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_declare(self, _find):
        plugin = Mock()
        _find.return_value = plugin
        name = 'test'
        queue = Queue(name)
        queue.durable = 1
        queue.auto_delete = 2
        queue.exclusive = 3

        # test
        queue.declare(TEST_URL)

        # validation
        plugin.Queue.assert_called_with(name)
        impl = plugin.Queue()
        impl.declare.assert_called_with(TEST_URL)
        self.assertEqual(impl.durable, queue.durable)
        self.assertEqual(impl.auto_delete, queue.auto_delete)
        self.assertEqual(impl.exclusive, queue.exclusive)

    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_delete(self, _find):
        plugin = Mock()
        _find.return_value = plugin
        name = 'test'

        # test
        queue = Queue(name)
        queue.delete(TEST_URL)

        # validation
        plugin.Queue.assert_called_with(name)
        impl = plugin.Queue()
        impl.delete.assert_called_with(TEST_URL)

    @patch('gofer.messaging.adapter.model.Reader')
    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_purge(self, _find, _reader):
        name = 'test'
        _find.return_value = Mock()
        queued = [
            Mock(),
            Mock(),
            None
        ]
        _reader.return_value.get.side_effect = queued

        # test
        queue = Queue(name)
        queue.purge(TEST_URL)

        # validation
        _reader.assert_called_once_with(queue, url=TEST_URL)
        _reader.return_value.open.assert_called_once_with()
        _reader.return_value.close.assert_called_once_with()
        queued[0].ack.assert_called_once_with()
        queued[1].ack.assert_called_once_with()


class TestBaseEndpoint(TestCase):

    @patch('gofer.messaging.adapter.model.uuid4')
    def test_init(self, _uuid4):
        _uuid4.return_value = '1234'
        endpoint = BaseEndpoint(TEST_URL)
        self.assertEqual(endpoint.url, TEST_URL)

    def test_is_open(self):
        endpoint = BaseEndpoint(TEST_URL)
        self.assertRaises(NotImplementedError, endpoint.is_open)

    def test_channel(self):
        endpoint = BaseEndpoint(TEST_URL)
        self.assertRaises(NotImplementedError, endpoint.channel)

    def test_open(self):
        endpoint = BaseEndpoint(TEST_URL)
        self.assertRaises(NotImplementedError, endpoint.open)

    def test_ack(self):
        endpoint = BaseEndpoint(TEST_URL)
        self.assertRaises(NotImplementedError, endpoint.ack, Mock())

    def test_reject(self):
        endpoint = BaseEndpoint(TEST_URL)
        self.assertRaises(NotImplementedError, endpoint.reject, Mock())

    def test_close(self):
        endpoint = BaseEndpoint(TEST_URL)
        self.assertRaises(NotImplementedError, endpoint.close)

    @patch('gofer.messaging.adapter.model.BaseEndpoint.open')
    def test_enter(self, _open):
        endpoint = BaseEndpoint(TEST_URL)
        retval = endpoint.__enter__()
        _open.assert_called_once_with()
        self.assertEqual(endpoint, retval)

    @patch('gofer.messaging.adapter.model.BaseEndpoint.close')
    def test_exit(self, _close):
        endpoint = BaseEndpoint(TEST_URL)
        endpoint.__exit__()
        _close.assert_called_with()


class TestMessenger(TestCase):

    def test_init(self):
        messenger = Messenger(TEST_URL)
        self.assertRaises(NotImplementedError, messenger.endpoint)
        self.assertRaises(NotImplementedError, messenger.link, Mock())
        self.assertRaises(NotImplementedError, messenger.unlink)
        self.assertTrue(isinstance(messenger, BaseEndpoint))

    @patch('gofer.messaging.adapter.model.Messenger.endpoint')
    def test_channel(self, _endpoint):
        messenger = Messenger(TEST_URL)
        channel = messenger.channel()
        _endpoint().channel.assert_called_with()
        self.assertEqual(channel, _endpoint().channel())

    @patch('gofer.messaging.adapter.model.Messenger.endpoint')
    def test_is_open(self, _endpoint):
        messenger = Messenger(TEST_URL)
        is_open = messenger.is_open()
        _endpoint().is_open.assert_called_with()
        self.assertEqual(is_open, _endpoint().is_open.return_value)

    @patch('gofer.messaging.adapter.model.Messenger.endpoint')
    def test_open(self, _endpoint):
        messenger = Messenger(TEST_URL)
        messenger.open()
        _endpoint().open.assert_called_with()

    @patch('gofer.messaging.adapter.model.Messenger.endpoint')
    def test_close(self, _endpoint):
        messenger = Messenger(TEST_URL)
        # soft
        messenger.close()
        _endpoint().close.assert_called_with(False)
        # hard
        _endpoint().close.reset_mock()
        messenger.close(True)
        _endpoint().close.assert_called_with(True)


class TestBaseReader(TestCase):

    def test_init(self):
        queue = Queue('')
        url = TEST_URL
        reader = BaseReader(queue, url)
        self.assertEqual(reader.queue, queue)
        self.assertEqual(reader.url, url)
        self.assertTrue(isinstance(reader, Messenger))

    def test_get(self):
        queue = Queue('')
        url = TEST_URL
        reader = BaseReader(queue, url)
        self.assertRaises(NotImplementedError, reader.get, 10)

    def test_ack(self):
        message = Mock()
        queue = Queue('')
        url = TEST_URL
        reader = BaseReader(queue, url)
        reader.endpoint = Mock()
        reader.ack(message)
        reader.endpoint.return_value.ack.assert_called_once_with(message)

    def test_reject(self):
        message = Mock()
        queue = Queue('')
        url = TEST_URL
        reader = BaseReader(queue, url)
        reader.endpoint = Mock()
        reader.reject(message, 29)
        reader.endpoint.return_value.reject.assert_called_once_with(message, 29)


class TestReader(TestCase):

    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_init(self, _find):
        _impl = Mock()
        plugin = Mock()
        plugin.Reader.return_value = _impl
        _find.return_value = plugin
        queue = BaseQueue('')
        url = TEST_URL

        # test
        reader = Reader(queue, url)

        # validation
        _find.assert_called_with(url)
        plugin.Reader.assert_called_with(queue, url)
        self.assertEqual(reader.authenticator, None)
        self.assertTrue(isinstance(reader, BaseReader))

    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_endpoint(self, _find):
        _impl = Mock()
        plugin = Mock()
        plugin.Reader.return_value = _impl
        _find.return_value = plugin
        queue = BaseQueue('')
        url = TEST_URL

        # test
        reader = Reader(queue, url)
        endpoint = reader.endpoint()

        # validation
        _impl.endpoint.assert_called_once_with()
        self.assertEqual(endpoint, _impl.endpoint.return_value)

    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_open(self, _find):
        _impl = Mock()
        plugin = Mock()
        plugin.Reader.return_value = _impl
        _find.return_value = plugin
        url = TEST_URL
        queue = BaseQueue('')
        reader = Reader(queue, url)
        reader.open()
        _impl.open.assert_called_with()

    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_ack(self, _find):
        _impl = Mock()
        plugin = Mock()
        plugin.Reader.return_value = _impl
        _find.return_value = plugin
        message = Mock()
        url = TEST_URL
        queue = BaseQueue('')
        reader = Reader(queue, url)
        reader.ack(message)
        message.ack.assert_called_once_with()

    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_reject(self, _find):
        _impl = Mock()
        plugin = Mock()
        plugin.Reader.return_value = _impl
        _find.return_value = plugin
        message = Mock()
        url = TEST_URL
        queue = BaseQueue('')
        reader = Reader(queue, url)
        reader.reject(message, 29)
        message.reject.assert_called_with(29)

    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_close(self, _find):
        _impl = Mock()
        plugin = Mock()
        plugin.Reader.return_value = _impl
        _find.return_value = plugin
        url = TEST_URL
        queue = BaseQueue('')
        reader = Reader(queue, url)
        # soft
        reader.close()
        _impl.close.assert_called_with(False)
        # hard
        _impl.close.reset_mock()
        reader.close(True)
        _impl.close.assert_called_with(True)

    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_get(self, _find):
        message = Mock()
        _impl = Mock()
        _impl.get.return_value = message
        plugin = Mock()
        plugin.Reader.return_value = _impl
        _find.return_value = plugin
        queue = BaseQueue('')
        url = TEST_URL

        # test
        reader = Reader(queue, url)

        # validation
        m = reader.get(10)
        _impl.get.assert_called_with(10)
        self.assertEqual(m, message)

    @patch('gofer.messaging.adapter.model.validate')
    @patch('gofer.messaging.adapter.model.auth')
    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_next(self, _find, auth, validate):
        _impl = Mock()
        plugin = Mock()
        plugin.Reader.return_value = _impl
        _find.return_value = plugin
        message = Mock(body='test-content')
        document = Mock()
        auth.validate.return_value = document

        # test
        reader = Reader(None)
        reader.get = Mock(return_value=message)
        reader.authenticator = Mock()
        _message, _document = reader.next(10)

        # validation
        reader.get.assert_called_once_with(10)
        auth.validate.assert_called_once_with(reader.authenticator, message.body)
        validate.assert_called_once_with(document)
        self.assertEqual(_message, reader.get.return_value)
        self.assertEqual(_document, document)

    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_next_not_found(self, _find):
        _impl = Mock()
        plugin = Mock()
        plugin.Reader.return_value = _impl
        _find.return_value = plugin

        # test
        reader = Reader(None)
        reader.get = Mock(return_value=None)
        reader.authenticator = Mock()
        _message, _document = reader.next(10)

        # validation
        reader.get.assert_called_once_with(10)
        self.assertEqual(_message, None)
        self.assertEqual(_document, None)

    @patch('gofer.messaging.adapter.model.validate')
    @patch('gofer.messaging.adapter.model.auth')
    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_next_auth_rejected(self, _find, auth, validate):
        _impl = Mock()
        plugin = Mock()
        plugin.Reader.return_value = _impl
        _find.return_value = plugin
        message = Mock(body='test-content')
        auth.validate.side_effect = ModelError

        # test
        reader = Reader(None)
        reader.get = Mock(return_value=message)
        reader.authenticator = Mock()
        self.assertRaises(ModelError, reader.next, 10)

        # validation
        reader.get.assert_called_once_with(10)
        auth.validate.assert_called_once_with(reader.authenticator, message.body)
        message.ack.assert_called_once_with()
        self.assertFalse(validate.called)

    @patch('gofer.messaging.adapter.model.validate')
    @patch('gofer.messaging.adapter.model.auth')
    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_next_invalid(self, _find, auth, validate):
        _impl = Mock()
        plugin = Mock()
        plugin.Reader.return_value = _impl
        _find.return_value = plugin
        message = Mock(body='test-content')
        document = Mock()
        auth.validate.return_value = document
        validate.side_effect = ModelError

        # test
        reader = Reader(None)
        reader.get = Mock(return_value=message)
        reader.authenticator = Mock()
        self.assertRaises(ModelError, reader.next, 10)

        # validation
        reader.get.assert_called_once_with(10)
        auth.validate.assert_called_once_with(reader.authenticator, message.body)
        message.ack.assert_called_once_with()
        validate.assert_called_once_with(document)

    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_search(self, _find):
        _impl = Mock()
        plugin = Mock()
        plugin.Reader.return_value = _impl
        _find.return_value = plugin
        received = [
            (Mock(), Document(sn='1')),
            (Mock(), Document(sn='2')),
            (Mock(), Document(sn='3'))
        ]

        # test
        url = TEST_URL
        queue = BaseQueue('')
        sn = received[1][1].sn
        reader = Reader(queue, url)
        reader.next = Mock(side_effect=received)
        document = reader.search(sn, timeout=10)

        # validation
        next_calls = reader.next.call_args_list
        self.assertEqual(len(next_calls), 2)
        self.assertEqual(document, received[1][1])
        for call in next_calls:
            self.assertEqual(call[0][0], 10)
        self.assertTrue(received[0][0].ack.called)
        self.assertTrue(received[1][0].ack.called)
        self.assertFalse(received[2][0].ack.called)

    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_search_not_found(self, _find):
        _impl = Mock()
        plugin = Mock()
        plugin.Reader.return_value = _impl
        _find.return_value = plugin
        received = [
            (Mock(), Document(sn='1')),
            (Mock(), Document(sn='2')),
            (Mock(), Document(sn='3')),
            (None, None)
        ]

        # test
        url = TEST_URL
        queue = BaseQueue('')
        reader = Reader(queue, url)
        reader.next = Mock(side_effect=received)
        document = reader.search('', timeout=10)

        # validation
        next_calls = reader.next.call_args_list
        self.assertEqual(len(next_calls), len(received))
        self.assertEqual(document, None)
        for call in next_calls:
            self.assertEqual(call[0][0], 10)
        self.assertTrue(received[0][0].ack.called)
        self.assertTrue(received[1][0].ack.called)
        self.assertTrue(received[2][0].ack.called)

    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_search_timeout(self, _find):
        _impl = Mock()
        plugin = Mock()
        plugin.Reader.return_value = _impl
        _find.return_value = plugin
        received = [
            (Mock(), Document(sn='1')),
            (Mock(), Document(sn='2')),
            (None, None)
        ]

        # test
        url = TEST_URL
        queue = BaseQueue('')
        reader = Reader(queue, url)
        reader.next = Mock(side_effect=received)
        document = reader.search('', timeout=10)

        # validation
        next_calls = reader.next.call_args_list
        self.assertEqual(len(next_calls), len(received))
        self.assertEqual(document, None)
        for call in next_calls:
            self.assertEqual(call[0][0], 10)
        self.assertTrue(received[0][0].ack.called)
        self.assertTrue(received[1][0].ack.called)


class TestBaseSender(TestCase):

    def test_init(self):
        url = TEST_URL
        sender = BaseSender(url)
        self.assertEqual(sender.url, url)
        self.assertTrue(isinstance(sender, Messenger))

    def test_abstract(self):
        url = TEST_URL
        sender = BaseSender(url)
        self.assertRaises(NotImplementedError, sender.send, None, None, None)


class TestSender(TestCase):

    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_init(self, _find):
        _impl = Mock()
        plugin = Mock()
        plugin.Sender.return_value = _impl
        _find.return_value = plugin
        url = TEST_URL
        sender = Sender(url)
        self.assertEqual(sender._impl, _impl)
        self.assertTrue(isinstance(sender, BaseSender))

    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_endpoint(self, _find):
        _impl = Mock()
        plugin = Mock()
        plugin.Sender.return_value = _impl
        _find.return_value = plugin
        url = TEST_URL

        # test
        sender = Sender(url)
        endpoint = sender.endpoint()

        # validation
        _impl.endpoint.assert_called_once_with()
        self.assertEqual(endpoint, _impl.endpoint.return_value)

    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_link(self, _find):
        _impl = Mock()
        plugin = Mock()
        plugin.Sender.return_value = _impl
        _find.return_value = plugin
        url = TEST_URL
        messenger = Mock()
        sender = Sender(url)
        sender.link(messenger)
        _impl.link.assert_called_with(messenger)

    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_unlink(self, _find):
        _impl = Mock()
        plugin = Mock()
        plugin.Sender.return_value = _impl
        _find.return_value = plugin
        url = TEST_URL
        sender = Sender(url)
        sender.unlink()
        _impl.unlink.assert_called_with()

    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_open(self, _find):
        _impl = Mock()
        plugin = Mock()
        plugin.Sender.return_value = _impl
        _find.return_value = plugin
        url = TEST_URL
        sender = Sender(url)
        sender.open()
        _impl.open.assert_called_with()

    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_close(self, _find):
        _impl = Mock()
        plugin = Mock()
        plugin.Sender.return_value = _impl
        _find.return_value = plugin
        url = TEST_URL
        sender = Sender(url)
        # soft
        sender.close()
        _impl.close.assert_called_with(False)
        # hard
        _impl.close.reset_mock()
        sender.close(True)
        _impl.close.assert_called_with(True)

    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_send(self, _find):
        _impl = Mock()
        plugin = Mock()
        plugin.Sender.return_value = _impl
        _find.return_value = plugin
        url = TEST_URL
        route = Mock()
        content = '1234'
        ttl = 10
        sender = Sender(url)
        sender.send(route, content, ttl)
        _impl.send.assert_called_once_with(route, content, ttl)


class TestProducer(TestCase):

    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_init(self, _find):
        _impl = Mock()
        plugin = Mock()
        plugin.Sender.return_value = _impl
        _find.return_value = plugin
        url = TEST_URL
        producer = Producer(url)
        _find.assert_called_with(url)
        self.assertEqual(producer.url, url)
        self.assertEqual(producer.authenticator, None)
        self.assertEqual(producer._impl, _impl)
        self.assertTrue(isinstance(producer, Messenger))

    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_endpoint(self, _find):
        _impl = Mock()
        plugin = Mock()
        plugin.Sender.return_value = _impl
        _find.return_value = plugin
        url = TEST_URL

        # test
        producer = Producer(url)
        endpoint = producer.endpoint()

        # validation
        _impl.endpoint.assert_called_once_with()
        self.assertEqual(endpoint, _impl.endpoint.return_value)

    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_link(self, _find):
        _impl = Mock()
        plugin = Mock()
        plugin.Sender.return_value = _impl
        _find.return_value = plugin
        url = TEST_URL
        messenger = Mock()
        producer = Producer(url)
        producer.link(messenger)
        _impl.link.assert_called_with(messenger)

    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_unlink(self, _find):
        _impl = Mock()
        plugin = Mock()
        plugin.Sender.return_value = _impl
        _find.return_value = plugin
        url = TEST_URL
        producer = Producer(url)
        producer.unlink()
        _impl.unlink.assert_called_with()

    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_open(self, _find):
        _impl = Mock()
        plugin = Mock()
        plugin.Sender.return_value = _impl
        _find.return_value = plugin
        url = TEST_URL
        producer = Producer(url)
        producer.open()
        _impl.open.assert_called_with()

    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_close(self, _find):
        _impl = Mock()
        plugin = Mock()
        plugin.Sender.return_value = _impl
        _find.return_value = plugin
        url = TEST_URL
        producer = Producer(url)
        # soft
        producer.close()
        _impl.close.assert_called_with(False)
        # hard
        _impl.close.reset_mock()
        producer.close(True)
        _impl.close.assert_called_with(True)

    @patch('gofer.messaging.adapter.model.Document')
    @patch('gofer.messaging.adapter.model.uuid4')
    @patch('gofer.messaging.adapter.model.auth')
    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_send(self, _find, auth, uuid4, document):
        _impl = Mock()
        _impl.send.return_value = '456'
        plugin = Mock()
        plugin.Sender.return_value = _impl
        _find.return_value = plugin
        uuid4.return_value = '<uuid>'
        route = 'amq.direct/bar'
        ttl = 234
        body = {'A': 1, 'B': 2}

        # test
        producer = Producer(TEST_URL)
        producer.authenticator = Mock()
        sn = producer.send(route, ttl=ttl, **body)

        # validation
        document.assert_called_once_with(
            sn=str(uuid4.return_value),
            version=VERSION,
            routing=(None, route)
        )
        unsigned = document.return_value
        auth.sign.assert_called_once_with(
            producer.authenticator, unsigned.__iadd__.return_value.dump.return_value)
        _impl.send.assert_called_once_with(route, auth.sign.return_value, ttl)
        self.assertEqual(sn, uuid4.return_value)


class TestBaseConnection(TestCase):

    def test_init(self):
        connection = BaseConnection(TEST_URL)
        self.assertEqual(connection.url, TEST_URL)

    def test_abstract(self):
        connection = BaseConnection(TEST_URL)
        self.assertRaises(NotImplementedError, connection.is_open)
        self.assertRaises(NotImplementedError, connection.open)
        self.assertRaises(NotImplementedError, connection.channel)
        self.assertRaises(NotImplementedError, connection.close)

    def test_str(self):
        connection = BaseConnection(TEST_URL)
        self.assertEqual(str(connection), TEST_URL)

    @patch('gofer.messaging.adapter.model.BaseConnection.open')
    def test_enter(self, _open):
        connection = BaseConnection(TEST_URL)
        retval = connection.__enter__()
        _open.assert_called_once_with()
        self.assertEqual(connection, retval)

    @patch('gofer.messaging.adapter.model.BaseConnection.close')
    def test_exit(self, _close):
        connection = BaseConnection(TEST_URL)
        connection.__exit__()
        _close.assert_called_with()


class TestConnection(TestCase):

    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_init(self, _find):
        _impl = Mock()
        plugin = Mock()
        plugin.Connection.return_value = _impl
        _find.return_value = plugin
        url = TEST_URL
        connection = Connection(url)
        _find.assert_called_with(url)
        self.assertEqual(connection.url, url)
        self.assertEqual(connection._impl, _impl)

    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_is_open(self, _find):
        _impl = Mock()
        plugin = Mock()
        plugin.Connection.return_value = _impl
        _find.return_value = plugin
        url = TEST_URL
        connection = Connection(url)
        is_open = connection.is_open()
        _impl.is_open.assert_called_once_with()
        self.assertEqual(is_open, _impl.is_open.return_value)

    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_open(self, _find):
        _impl = Mock()
        plugin = Mock()
        plugin.Connection.return_value = _impl
        _find.return_value = plugin
        url = TEST_URL
        connection = Connection(url)
        connection.open()
        _impl.open.assert_called_once_with()

    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_channel(self, _find):
        _impl = Mock()
        plugin = Mock()
        plugin.Connection.return_value = _impl
        _find.return_value = plugin
        url = TEST_URL
        connection = Connection(url)
        channel = connection.channel()
        _impl.channel.assert_called_once_with()
        self.assertEqual(channel, _impl.channel.return_value)

    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_close(self, _find):
        _impl = Mock()
        plugin = Mock()
        plugin.Connection.return_value = _impl
        _find.return_value = plugin
        url = TEST_URL
        connection = Connection(url)
        # soft
        connection.close()
        _impl.close.assert_called_once_with(False)
        # hard
        _impl.close.reset_mock()
        connection.close(True)
        _impl.close.assert_called_once_with(True)


class TestSharedConnection(TestCase):

    def test_connections(self):
        connection = SharedConnection('fake', (), {})
        # create (local.d)
        self.assertEqual(connection.connections, connection.local.d)
        self.assertTrue(isinstance(connection, SharedConnection))
        # already created
        self.assertEqual(connection.connections, connection.local.d)
        self.assertTrue(isinstance(connection, SharedConnection))

    def test_call(self):
        url = TEST_URL
        fake1 = FakeConnection(url)
        fake2 = FakeConnection(url)
        fake3 = FakeConnection('')
        self.assertEqual(fake1, fake2)
        self.assertNotEqual(fake1, fake3)


class TestSSL(TestCase):

    def test_init(self):
        ssl = SSL()
        self.assertEqual(ssl.ca_certificate, None)
        self.assertEqual(ssl.client_key, None)
        self.assertEqual(ssl.client_certificate, None)
        self.assertFalse(ssl.host_validation)

    def test_str(self):
        ssl = SSL()
        ssl.ca_certificate = 'test-ca'
        ssl.client_key = 'test-key'
        ssl.client_certificate = 'test-cert'
        self.assertEqual(
            str(ssl),
            'ca: test-ca|key: test-key|certificate: test-cert|host-validation: False')


class TestBroker(TestCase):

    def test_init(self):
        url = TEST_URL
        b = Broker(url)
        self.assertEqual(b.url, URL(url))
        self.assertEqual(b.adapter, URL(url).adapter)
        self.assertEqual(b.scheme, URL(url).scheme)
        self.assertEqual(b.host, URL(url).host)
        self.assertEqual(b.port, URL(url).port)
        self.assertEqual(b.userid, URL(url).userid)
        self.assertEqual(b.password, URL(url).password)
        self.assertEqual(b.virtual_host, URL(url).path)
        self.assertEqual(b.ssl.ca_certificate, None)
        self.assertEqual(b.ssl.client_key, None)
        self.assertEqual(b.ssl.client_certificate, None)
        self.assertFalse(b.ssl.host_validation)

    def test_str(self):
        url = TEST_URL
        b = Broker(url)
        b.ssl.ca_certificate = 'test-ca'
        b.ssl.client_key = 'test-key'
        b.ssl.client_certificate = 'test-cert'
        self.assertEqual(
            str(b),
            'URL: qpid+amqp://elmer:fudd@test.com/test|SSL: ca: test-ca|'
            'key: test-key|certificate: test-cert|host-validation: False')

    def test_domain_id(self):
        url = 'amqp://localhost'
        b = Broker(url)
        self.assertEqual(b.domain_id, url)


class TestMessage(TestCase):

    def test_init(self):
        reader = Mock()
        impl = Mock()
        body = 'test-body'
        message = Message(reader, impl, body)
        self.assertEqual(message._reader, reader)
        self.assertEqual(message._impl, impl)
        self.assertEqual(message._body, body)

    def test_body(self):
        reader = Mock()
        impl = Mock()
        body = 'test-body'
        message = Message(reader, impl, body)
        self.assertEqual(message.body, body)

    def test_accept(self):
        reader = Mock()
        impl = Mock()
        body = 'test-body'
        message = Message(reader, impl, body)
        message.ack()
        reader.ack.assert_called_with(impl)

    def test_reject(self):
        reader = Mock()
        impl = Mock()
        body = 'test-body'
        message = Message(reader, impl, body)
        message.reject(True)
        reader.reject.assert_called_with(impl, True)

    def test_str(self):
        reader = Mock()
        impl = Mock()
        body = 'test-body'
        message = Message(reader, impl, body)
        self.assertEqual(str(message), body)