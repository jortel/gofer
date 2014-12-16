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

from gofer.messaging.model import Document
from gofer.messaging.adapter.url import URL
from gofer.messaging.adapter.model import Destination
from gofer.messaging.adapter.model import Model, _Domain, Node
from gofer.messaging.adapter.model import BaseExchange, Exchange
from gofer.messaging.adapter.model import BaseQueue, Queue
from gofer.messaging.adapter.model import BaseEndpoint, Messenger
from gofer.messaging.adapter.model import BaseReader, Reader
from gofer.messaging.adapter.model import BaseProducer, Producer
from gofer.messaging.adapter.model import BasePlainProducer, PlainProducer
from gofer.messaging.adapter.model import Broker, SSL
from gofer.messaging.adapter.model import BaseConnection, Connection, SharedConnection
from gofer.messaging.adapter.model import Message
from gofer.messaging.adapter.model import ModelError
from gofer.messaging.adapter.model import model, blocking, managed, DELAY, DELAY_MULTIPLIER


TEST_URL = 'qpid+amqp://elmer:fudd@test.com/test'


class Local(object):
    pass


class FakeConnection(object):

    __metaclass__ = SharedConnection

    def __init__(self, url):
        self.url = url


# --- decorators -------------------------------------------------------------


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


class TestManagedDecorator(TestCase):

    def test_call(self):
        fn = Mock()
        node = Mock(domain_id='node')
        _fn = managed(fn)
        args = [node, 2, 3]
        keywords = dict(a=1, b=2)
        ret = _fn(*args, **keywords)
        fn.assert_called_once_with(*args, **keywords)
        self.assertEqual(ret, fn.return_value)

    @patch('gofer.messaging.adapter.model._Domain.contains')
    def test_not_called(self, contains):
        fn = Mock()
        node = Mock(domain_id='node')
        contains.return_value = True
        _fn = managed(fn)
        args = [node, 2, 3]
        keywords = dict(a=1, b=2)
        _fn(*args, **keywords)
        self.assertFalse(fn.called)


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


# --- domain -----------------------------------------------------------------


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


# --- destination ------------------------------------------------------------


class TestDestination(TestCase):

    def test_create(self):
        d = {Destination.EXCHANGE: 1, Destination.ROUTING_KEY: 2}
        destination = Destination.create(d)
        self.assertEqual(destination.exchange, d[Destination.EXCHANGE])
        self.assertEqual(destination.routing_key, d[Destination.ROUTING_KEY])

    def test_init(self):
        exchange = 'EX'
        routing_key = 'RK'
        # both
        d = Destination(routing_key, exchange=exchange)
        self.assertEqual(d.routing_key, routing_key)
        self.assertEqual(d.exchange, exchange)
        # routing_key
        d = Destination(routing_key)
        self.assertEqual(d.routing_key, routing_key)
        self.assertEqual(d.exchange, '')

    def test_dict(self):
        exchange = 'EX'
        routing_key = 'RK'
        d = Destination(routing_key, exchange)
        self.assertEqual(
            d.dict(),
            {Destination.EXCHANGE: exchange, Destination.ROUTING_KEY: routing_key})

    def test_eq(self):
        self.assertTrue(Destination('1', '2') == Destination('1', '2'))
        self.assertFalse(Destination('1', '0') == Destination('1', '2'))

    def test_neq(self):
        self.assertTrue(Destination('1', '0') != Destination('1', '2'))
        self.assertFalse(Destination('1', '2') != Destination('1', '2'))

    def test_str(self):
        d = Destination('1', '2')
        self.assertEqual(str(d), str(d.__dict__))

    def test_repr(self):
        d = Destination('1', '2')
        self.assertEqual(repr(d), repr(d.__dict__))


# --- node ---------------------------------------------------------


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


# --- exchange ---------------------------------------------------------------


class TestBaseExchange(TestCase):

    def test_init(self):
        name = 'test'
        exchange = BaseExchange(name)
        self.assertEqual(exchange.name, name)
        self.assertEqual(exchange.policy, None)
        # with policy
        policy = 'direct'
        exchange = BaseExchange(name, policy=policy)
        self.assertEqual(exchange.name, name)
        self.assertEqual(exchange.policy, policy)

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
        self.assertEqual(exchange.policy, None)
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
        plugin.Exchange.assert_called_with(exchange.name, policy=exchange.policy)
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
        plugin.Exchange.assert_called_with(exchange.name)
        impl = plugin.Exchange()
        impl.delete.assert_called_with(TEST_URL)


# --- queue ------------------------------------------------------------------


class TestBaseQueue(TestCase):

    def test_init(self):
        name = 'test'
        exchange = Exchange('amq.direct')
        routing_key = name
        queue = BaseQueue(name, exchange, routing_key)
        self.assertEqual(queue.name, name)
        self.assertEqual(queue.exchange, exchange)
        self.assertEqual(queue.routing_key, routing_key)

    def test_destination(self):
        name = 'test'
        exchange = Exchange('amq.direct')
        routing_key = name
        queue = BaseQueue(name, exchange, routing_key)
        self.assertRaises(NotImplementedError, queue.destination, '')

    def test_eq(self):
        self.assertTrue(BaseQueue('1', Exchange(''), 'RK') == BaseQueue('1', Exchange(''), 'XX'))
        self.assertFalse(BaseQueue('1', Exchange(''), 'RK') == BaseQueue('2', Exchange(''), 'RK'))

    def test_neq(self):
        self.assertTrue(BaseQueue('1', Exchange(''), 'RK') != BaseQueue('2', Exchange(''), 'XX'))
        self.assertFalse(BaseQueue('1', Exchange(''), 'RK') != BaseQueue('1', Exchange(''), 'RK'))


class TestQueue(TestCase):

    def test_init(self):
        name = 'test'
        exchange = Exchange('amq.direct')
        routing_key = name
        # just name
        queue = Queue(name)
        self.assertEqual(queue.name, name)
        self.assertEqual(queue.exchange, None)
        self.assertEqual(queue.routing_key, None)
        # all parameters
        queue = Queue(name, exchange, routing_key)
        self.assertEqual(queue.name, name)
        self.assertEqual(queue.exchange, exchange)
        self.assertEqual(queue.routing_key, routing_key)

    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_declare(self, _find):
        plugin = Mock()
        _find.return_value = plugin
        name = 'test'
        exchange = Exchange('test')
        routing_key = name
        queue = Queue(name, exchange, routing_key)
        queue.durable = 1
        queue.auto_delete = 2
        queue.exclusive = 3

        # test
        queue.declare(TEST_URL)

        # validation
        plugin.Queue.assert_called_with(name, exchange, routing_key)
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
        queue.purge = Mock()
        queue.delete(TEST_URL)

        # validation
        plugin.Queue.assert_called_with(name)
        queue.purge.assert_called_once_with(TEST_URL)
        impl = plugin.Queue()
        impl.delete.assert_called_with(TEST_URL)

    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_destination(self, _find):
        _impl = Mock()
        plugin = Mock()
        plugin.Queue.return_value = _impl
        _impl.destination.return_value = Mock()
        _find.return_value = plugin
        name = 'test'
        exchange = Exchange('test')
        routing_key = name
        queue = Queue(name, exchange, routing_key)

        # test
        destination = queue.destination(TEST_URL)

        # validation
        plugin.Queue.assert_called_with(name, exchange, routing_key)
        _impl.destination.assert_called_with(TEST_URL)
        self.assertEqual(destination, _impl.destination())

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


# --- endpoint ---------------------------------------------------------------


class TestBaseEndpoint(TestCase):

    @patch('gofer.messaging.adapter.model.uuid4')
    def test_init(self, _uuid4):
        _uuid4.return_value = '1234'
        endpoint = BaseEndpoint(TEST_URL)
        self.assertEqual(endpoint.url, TEST_URL)
        self.assertEqual(endpoint.uuid, str(_uuid4()))
        self.assertEqual(endpoint.authenticator, None)

    @patch('gofer.messaging.adapter.model.uuid4')
    def test_id(self, _uuid4):
        _uuid4.return_value = '1234'
        endpoint = BaseEndpoint(TEST_URL)
        self.assertEqual(endpoint.id(), endpoint.uuid)

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


# --- reader -----------------------------------------------------------------


class TestMessenger(TestCase):

    def test_endpoint(self):
        messenger = Messenger(TEST_URL)
        self.assertRaises(NotImplementedError, messenger.endpoint)

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


# --- messenger --------------------------------------------------------------


class TestBaseReader(TestCase):

    def test_init(self):
        queue = Queue('')
        url = TEST_URL
        reader = BaseReader(queue, url)
        self.assertEqual(reader.queue, queue)
        self.assertEqual(reader.url, url)

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
        queue = BaseQueue('', Exchange(''), '')
        url = TEST_URL

        # test
        Reader(queue, url)

        # validation
        _find.assert_called_with(url)
        plugin.Reader.assert_called_with(queue, url)

    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_channel(self, _find):
        _impl = Mock()
        _impl.channel.return_value = Mock()
        plugin = Mock()
        plugin.Reader.return_value = _impl
        _find.return_value = plugin
        url = TEST_URL

        # test
        queue = BaseQueue('', Exchange(''), '')
        reader = Reader(queue, url)
        channel = reader.channel()

        # validation
        _impl.channel.assert_called_with()
        self.assertEqual(channel, _impl.channel())

    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_open(self, _find):
        _impl = Mock()
        plugin = Mock()
        plugin.Reader.return_value = _impl
        _find.return_value = plugin
        url = TEST_URL
        queue = BaseQueue('', Exchange(''), '')
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
        queue = BaseQueue('', Exchange(''), '')
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
        queue = BaseQueue('', Exchange(''), '')
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
        queue = BaseQueue('', Exchange(''), '')
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
        queue = BaseQueue('', Exchange(''), '')
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
        queue = BaseQueue('', Exchange(''), '')
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
        queue = BaseQueue('', Exchange(''), '')
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
        queue = BaseQueue('', Exchange(''), '')
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


# --- producer ---------------------------------------------------------------


class TestBaseProducer(TestCase):

    @patch('gofer.messaging.adapter.model.uuid4')
    def test_init(self, _uuid4):
        _uuid4.return_value = '1234'
        producer = BaseProducer(TEST_URL)
        self.assertEqual(producer.url, TEST_URL)
        self.assertEqual(producer.uuid, str(_uuid4()))
        self.assertEqual(producer.authenticator, None)

    def test_send(self):
        producer = BaseProducer(TEST_URL)
        self.assertRaises(NotImplementedError, producer.send, None, 0)

    def test_broadcast(self):
        producer = BaseProducer(TEST_URL)
        self.assertRaises(NotImplementedError, producer.broadcast, [], 0)


class TestProducer(TestCase):

    @patch('gofer.messaging.adapter.model.uuid4')
    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_init(self, _find, _uuid4):
        _impl = Mock()
        plugin = Mock()
        plugin.Producer.return_value = _impl
        _find.return_value = plugin
        _uuid4.return_value = '1234'
        url = TEST_URL
        producer = Producer(url)
        _find.assert_called_with(url)
        self.assertEqual(producer.url, url)
        self.assertEqual(producer.uuid, str(_uuid4()))
        self.assertEqual(producer.authenticator, None)
        self.assertEqual(producer._impl, _impl)

    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_channel(self, _find):
        _impl = Mock()
        _impl.channel.return_value = Mock()
        plugin = Mock()
        plugin.Producer.return_value = _impl
        _find.return_value = plugin
        url = TEST_URL
        producer = Producer(url)
        channel = producer.channel()
        _impl.channel.assert_called_with()
        self.assertEqual(channel, _impl.channel())

    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_open(self, _find):
        _impl = Mock()
        plugin = Mock()
        plugin.Producer.return_value = _impl
        _find.return_value = plugin
        url = TEST_URL
        producer = Producer(url)
        producer.open()
        _impl.open.assert_called_with()

    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_close(self, _find):
        _impl = Mock()
        plugin = Mock()
        plugin.Producer.return_value = _impl
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

    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_send(self, _find):
        _impl = Mock()
        _impl.send.return_value = '456'
        plugin = Mock()
        plugin.Producer.return_value = _impl
        _find.return_value = plugin
        destination = Destination('')
        ttl = 234
        body = {'A': 1, 'B': 2}
        producer = Producer(TEST_URL)
        sn = producer.send(destination, ttl=ttl, **body)
        _impl.send.assert_called_with(destination, ttl, **body)
        self.assertEqual(sn, _impl.send())

    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_broadcast(self, _find):
        _impl = Mock()
        _impl.broadcast.return_value = ['456']
        plugin = Mock()
        plugin.Producer.return_value = _impl
        _find.return_value = plugin
        destination = Destination('')
        ttl = 234
        body = {'A': 1, 'B': 2}
        producer = Producer(TEST_URL)
        sn_list = producer.broadcast([destination], ttl=ttl, **body)
        _impl.broadcast.assert_called_with([destination], ttl, **body)
        self.assertEqual(sn_list, _impl.broadcast())


# --- plain producer ---------------------------------------------------------


class TestBasePlainProducer(TestCase):

    @patch('gofer.messaging.adapter.model.uuid4')
    def test_init(self, _uuid4):
        _uuid4.return_value = '1234'
        producer = BasePlainProducer(TEST_URL)
        self.assertEqual(producer.url, TEST_URL)
        self.assertEqual(producer.uuid, str(_uuid4()))
        self.assertEqual(producer.authenticator, None)

    def test_send(self):
        producer = BasePlainProducer(TEST_URL)
        self.assertRaises(NotImplementedError, producer.send, None, None, 0)

    def test_broadcast(self):
        producer = BasePlainProducer(TEST_URL)
        self.assertRaises(NotImplementedError, producer.broadcast, [], None, 0)


class TestPlainProducer(TestCase):

    @patch('gofer.messaging.adapter.model.uuid4')
    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_init(self, _find, _uuid4):
        _impl = Mock()
        plugin = Mock()
        plugin.PlainProducer.return_value = _impl
        _find.return_value = plugin
        _uuid4.return_value = '1234'
        url = TEST_URL
        producer = PlainProducer(url)
        _find.assert_called_with(url)
        self.assertEqual(producer.url, url)
        self.assertEqual(producer.uuid, str(_uuid4()))
        self.assertEqual(producer.authenticator, None)
        self.assertEqual(producer._impl, _impl)

    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_channel(self, _find):
        _impl = Mock()
        _impl.channel.return_value = Mock()
        plugin = Mock()
        plugin.PlainProducer.return_value = _impl
        _find.return_value = plugin
        url = TEST_URL
        producer = PlainProducer(url)
        channel = producer.channel()
        _impl.channel.assert_called_with()
        self.assertEqual(channel, _impl.channel())

    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_open(self, _find):
        _impl = Mock()
        plugin = Mock()
        plugin.PlainProducer.return_value = _impl
        _find.return_value = plugin
        url = TEST_URL
        producer = PlainProducer(url)
        producer.open()
        _impl.open.assert_called_with()

    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_close(self, _find):
        _impl = Mock()
        plugin = Mock()
        plugin.PlainProducer.return_value = _impl
        _find.return_value = plugin
        url = TEST_URL
        producer = PlainProducer(url)
        # soft
        producer.close()
        _impl.close.assert_called_with(False)
        # hard
        _impl.close.reset_mock()
        producer.close(True)
        _impl.close.assert_called_with(True)

    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_send(self, _find):
        _impl = Mock()
        _impl.send.return_value = '456'
        plugin = Mock()
        plugin.PlainProducer.return_value = _impl
        _find.return_value = plugin
        destination = Destination('')
        ttl = 234
        content = Mock()
        producer = PlainProducer(TEST_URL)
        sn = producer.send(destination, content, ttl=ttl)
        _impl.send.assert_called_with(destination, content, ttl)
        self.assertEqual(sn, _impl.send())


    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_broadcast(self, _find):
        _impl = Mock()
        _impl.broadcast.return_value = ['456']
        plugin = Mock()
        plugin.PlainProducer.return_value = _impl
        _find.return_value = plugin
        destination = Destination('')
        ttl = 234
        content = Mock()
        producer = PlainProducer(TEST_URL)
        sn_list = producer.broadcast([destination], content, ttl=ttl)
        _impl.broadcast.assert_called_with([destination], content, ttl)
        self.assertEqual(sn_list, _impl.broadcast())


# --- connection -------------------------------------------------------------


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


# --- broker -----------------------------------------------------------------


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


# --- message ----------------------------------------------------------------


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