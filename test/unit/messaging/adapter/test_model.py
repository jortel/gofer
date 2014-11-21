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
from gofer.messaging.adapter.model import Node
from gofer.messaging.adapter.model import BaseExchange, Exchange
from gofer.messaging.adapter.model import BaseQueue, Queue
from gofer.messaging.adapter.model import BaseEndpoint, Messenger
from gofer.messaging.adapter.model import BaseReader, Reader
from gofer.messaging.adapter.model import BaseProducer, Producer
from gofer.messaging.adapter.model import BasePlainProducer, PlainProducer
from gofer.messaging.adapter.model import BaseBroker, BrokerSingleton, Broker
from gofer.messaging.adapter.model import Ack
from gofer.messaging.adapter.model import DEFAULT_URL


TEST_URL = 'qpid+amqp://elmer:fudd@test.com/test'


class TestDestination(TestCase):

    def test_create(self):
        d = {Destination.EXCHANGE: 1, Destination.ROUTING_KEY: 2}
        destination = Destination.create(d)
        self.assertEqual(destination.exchange, d[Destination.EXCHANGE])
        self.assertEqual(destination.routing_key, d[Destination.ROUTING_KEY])

    def test_construction(self):
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

    def test_construction(self):
        name = 'test'
        n = Node(name)
        self.assertEqual(n.name, name)

    def test_abstract(self):
        n = Node('test')
        self.assertRaises(NotImplementedError, n.declare, '')
        self.assertRaises(NotImplementedError, n.delete, '')


# --- exchange ---------------------------------------------------------------


class TestBaseExchange(TestCase):

    def test_construction(self):
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

    def test_construction(self):
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
        exchange.declare(TEST_URL)
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
        exchange.delete(TEST_URL)
        plugin.Exchange.assert_called_with(exchange.name)
        impl = plugin.Exchange()
        impl.delete.assert_called_with(TEST_URL)


# --- queue ------------------------------------------------------------------


class TestBaseQueue(TestCase):

    def test_construction(self):
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

    def test_construction(self):
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
        queue.declare(TEST_URL)
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
        queue = Queue(name)
        queue.delete(TEST_URL)
        plugin.Queue.assert_called_with(name)
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
        destination = queue.destination(TEST_URL)
        plugin.Queue.assert_called_with(name, exchange, routing_key)
        _impl.destination.assert_called_with(TEST_URL)
        self.assertEqual(destination, _impl.destination())


# --- endpoint ---------------------------------------------------------------


class TestBaseEndpoint(TestCase):

    @patch('gofer.messaging.adapter.model.uuid4')
    def test_construction(self, _uuid4):
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

    def test_enter(self):
        endpoint = BaseEndpoint(TEST_URL)
        self.assertEqual(endpoint, endpoint.__enter__())

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
    def test_open(self, _endpoint):
        messenger = Messenger(TEST_URL)
        messenger.open()
        _endpoint().open.assert_called_with()

    @patch('gofer.messaging.adapter.model.Messenger.endpoint')
    def test_ack(self, _endpoint):
        message = 'hello'
        messenger = Messenger(TEST_URL)
        messenger.ack(message)
        _endpoint().ack.assert_called_with(message)

    @patch('gofer.messaging.adapter.model.Messenger.endpoint')
    def test_reject(self, _endpoint):
        message = 'hello'
        messenger = Messenger(TEST_URL)
        messenger.reject(message, True)
        _endpoint().reject.assert_called_with(message, True)

    @patch('gofer.messaging.adapter.model.Messenger.endpoint')
    def test_close(self, _endpoint):
        messenger = Messenger(TEST_URL)
        messenger.close()
        _endpoint().close.assert_called_with()


# --- messenger --------------------------------------------------------------


class TestBaseReader(TestCase):

    def test_construction(self):
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

    def test_next(self):
        queue = Queue('')
        url = TEST_URL
        reader = BaseReader(queue, url)
        self.assertRaises(NotImplementedError, reader.next, 10)

    def test_search(self):
        queue = Queue('')
        url = TEST_URL
        reader = BaseReader(queue, url)
        self.assertRaises(NotImplementedError, reader.search, None, 10)


class TestReader(TestCase):

    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_construction(self, _find):
        _impl = Mock()
        plugin = Mock()
        plugin.Reader.return_value = _impl
        _find.return_value = plugin
        queue = BaseQueue('', Exchange(''), '')
        url = TEST_URL
        Reader(queue, url)
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
        queue = BaseQueue('', Exchange(''), '')
        reader = Reader(queue, url)
        channel = reader.channel()
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
        message = Mock()
        _impl = Mock()
        plugin = Mock()
        plugin.Reader.return_value = _impl
        _find.return_value = plugin
        url = TEST_URL
        queue = BaseQueue('', Exchange(''), '')
        reader = Reader(queue, url)
        reader.ack(message)
        _impl.ack.assert_called_with(message)

    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_reject(self, _find):
        message = Mock()
        _impl = Mock()
        plugin = Mock()
        plugin.Reader.return_value = _impl
        _find.return_value = plugin
        url = TEST_URL
        queue = BaseQueue('', Exchange(''), '')
        reader = Reader(queue, url)
        reader.reject(message, True)
        _impl.reject.assert_called_with(message, True)

    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_close(self, _find):
        _impl = Mock()
        plugin = Mock()
        plugin.Reader.return_value = _impl
        _find.return_value = plugin
        url = TEST_URL
        queue = BaseQueue('', Exchange(''), '')
        reader = Reader(queue, url)
        reader.close()
        _impl.close.assert_called_with()


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
        reader = Reader(queue, url)
        m = reader.get(10)
        _impl.get.assert_called_with(10)
        self.assertEqual(m, message)

    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_next(self, _find):
        ack = Mock()
        document = Mock()
        _impl = Mock()
        _impl.next.return_value = document, ack
        plugin = Mock()
        plugin.Reader.return_value = _impl
        _find.return_value = plugin
        queue = BaseQueue('', Exchange(''), '')
        url = TEST_URL
        reader = Reader(queue, url)
        retval = reader.next(timeout=10)
        _impl.next.assert_called_with(10)
        self.assertEqual(retval[0], document)
        self.assertEqual(retval[1], ack)

    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_search(self, _find):
        received = [
            (Document(sn='1'), Mock()),
            (Document(sn='2'), Mock()),
            (Document(sn='3'), Mock())
        ]
        _impl = Mock()
        _impl.next.side_effect = received
        plugin = Mock()
        plugin.Reader.return_value = _impl
        _find.return_value = plugin
        queue = BaseQueue('', Exchange(''), '')
        url = TEST_URL
        sn = received[1][0].sn
        reader = Reader(queue, url)
        document = reader.search(sn, timeout=10)
        next_calls = _impl.next.call_args_list
        self.assertEqual(len(next_calls), 2)
        self.assertEqual(document, received[1][0])
        for call in next_calls:
            self.assertEqual(call[0][0], 10)
        self.assertTrue(received[0][1].called)
        self.assertTrue(received[1][1].called)
        self.assertFalse(received[2][1].called)

    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_search_timeout(self, _find):
        _impl = Mock()
        _impl.next.return_value = (None, None)
        plugin = Mock()
        plugin.Reader.return_value = _impl
        _find.return_value = plugin
        queue = BaseQueue('', Exchange(''), '')
        url = TEST_URL
        sn = 'serial'
        reader = Reader(queue, url)
        document = reader.search(sn, timeout=10)
        _impl.next.assert_called_once_with(10)
        self.assertEqual(document, None)


# --- producer ---------------------------------------------------------------


class TestBaseProducer(TestCase):

    @patch('gofer.messaging.adapter.model.uuid4')
    def test_construction(self, _uuid4):
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
    def test_construction(self, _find, _uuid4):
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
    def test_ack(self, _find):
        message = Mock()
        _impl = Mock()
        plugin = Mock()
        plugin.Producer.return_value = _impl
        _find.return_value = plugin
        url = TEST_URL
        producer = Producer(url)
        producer.ack(message)
        _impl.ack.assert_called_with(message)

    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_reject(self, _find):
        message = Mock()
        _impl = Mock()
        plugin = Mock()
        plugin.Producer.return_value = _impl
        _find.return_value = plugin
        url = TEST_URL
        producer = Producer(url)
        producer.reject(message, True)
        _impl.reject.assert_called_with(message, True)

    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_close(self, _find):
        _impl = Mock()
        plugin = Mock()
        plugin.Producer.return_value = _impl
        _find.return_value = plugin
        url = TEST_URL
        producer = Producer(url)
        producer.close()
        _impl.close.assert_called_with()

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
    def test_construction(self, _uuid4):
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
    def test_construction(self, _find, _uuid4):
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
    def test_ack(self, _find):
        message = Mock()
        _impl = Mock()
        plugin = Mock()
        plugin.PlainProducer.return_value = _impl
        _find.return_value = plugin
        url = TEST_URL
        producer = PlainProducer(url)
        producer.ack(message)
        _impl.ack.assert_called_with(message)

    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_reject(self, _find):
        message = Mock()
        _impl = Mock()
        plugin = Mock()
        plugin.PlainProducer.return_value = _impl
        _find.return_value = plugin
        url = TEST_URL
        producer = PlainProducer(url)
        producer.reject(message, True)
        _impl.reject.assert_called_with(message, True)

    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_close(self, _find):
        _impl = Mock()
        plugin = Mock()
        plugin.PlainProducer.return_value = _impl
        _find.return_value = plugin
        url = TEST_URL
        producer = PlainProducer(url)
        producer.close()
        _impl.close.assert_called_with()

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


# --- broker -----------------------------------------------------------------


class TestBrokerSingleton(TestCase):

    def test_string_key(self):
        # string
        url = 'http://host'
        key = BrokerSingleton.key([url], None)
        self.assertEqual(key, url)
        # url
        key = BrokerSingleton.key([URL(url)], None)
        self.assertEqual(key, url)
        # invalid
        self.assertRaises(ValueError, BrokerSingleton.key, [10], None)

    def test_call(self):
        class TestBroker(BaseBroker):
            def __init__(self, url=TEST_URL):
                BaseBroker.__init__(self, url)
        broker = TestBroker()
        self.assertEqual(broker.url, URL(DEFAULT_URL))


class TestBaseBroker(TestCase):

    def test_construction(self):
        url = TEST_URL
        BrokerSingleton.reset()
        b = BaseBroker(url)
        self.assertEqual(b.url, URL(url))
        self.assertEqual(b.id, URL(url).simple())
        self.assertEqual(b.adapter, URL(url).adapter)
        self.assertEqual(b.scheme, URL(url).scheme)
        self.assertEqual(b.host, URL(url).host)
        self.assertEqual(b.port, URL(url).port)
        self.assertEqual(b.userid, URL(url).userid)
        self.assertEqual(b.password, URL(url).password)
        self.assertEqual(b.virtual_host, URL(url).path)
        self.assertEqual(b.cacert, None)
        self.assertEqual(b.clientkey, None)
        self.assertEqual(b.clientcert, None)
        self.assertFalse(b.host_validation)

    def test_str(self):
        BrokerSingleton.reset()
        b = BaseBroker(TEST_URL)
        s = 'url=qpid+amqp://elmer:fudd@test.com/test|cacert=None|clientkey=None|' \
            'clientcert=None|host-validation=False'
        self.assertEqual(str(b), s)


class TestBroker(TestCase):

    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_construction(self, _find):
        plugin = Mock()
        _find.return_value = plugin
        url = TEST_URL
        BrokerSingleton.reset()
        b = Broker(url)
        _find.assert_called_with(url)
        plugin.Broker.assert_called_with(url)
        self.assertEqual(b.url, URL(url))
        self.assertEqual(b.id, URL(url).simple())
        self.assertEqual(b.adapter, URL(url).adapter)
        self.assertEqual(b.scheme, URL(url).scheme)
        self.assertEqual(b.host, URL(url).host)
        self.assertEqual(b.port, URL(url).port)
        self.assertEqual(b.userid, URL(url).userid)
        self.assertEqual(b.password, URL(url).password)
        self.assertEqual(b.virtual_host, URL(url).path)
        self.assertEqual(b.cacert, None)
        self.assertEqual(b.clientkey, None)
        self.assertEqual(b.clientcert, None)
        self.assertFalse(b.host_validation)
        self.assertEqual(b._impl, plugin.Broker())

    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_connect(self, _find):
        plugin = Mock()
        _find.return_value = plugin
        BrokerSingleton.reset()
        b = Broker(TEST_URL)
        b.cacert = 1
        b.clientkey = 2
        b.clientcert = 3
        b.host_validation = 4
        b.connect()
        b._impl.connect.assert_called_with()
        self.assertEqual(b._impl.cacert, b.cacert)
        self.assertEqual(b._impl.clientkey, b.clientkey)
        self.assertEqual(b._impl.clientcert, b.clientcert)
        self.assertEqual(b._impl.host_validation, b.host_validation)

    @patch('gofer.messaging.adapter.model.Adapter.find')
    def test_close(self, _find):
        plugin = Mock()
        _find.return_value = plugin
        BrokerSingleton.reset()
        b = Broker(TEST_URL)
        b.close()
        b._impl.close.assert_called_with()


# --- ack --------------------------------------------------------------------


class TestAck(TestCase):

    def test_construction(self):
        endpoint = Mock()
        message = Mock()
        ack = Ack(endpoint, message)
        self.assertEqual(ack.endpoint, endpoint)
        self.assertEqual(ack.message, message)

    def test_call(self):
        endpoint = Mock()
        message = Mock()
        ack = Ack(endpoint, message)
        ack()
        endpoint.ack.assert_called_with(message)

    def test_accept(self):
        endpoint = Mock()
        message = Mock()
        ack = Ack(endpoint, message)
        ack.accept()
        endpoint.ack.assert_called_with(message)

    def test_reject(self):
        endpoint = Mock()
        message = Mock()
        ack = Ack(endpoint, message)
        ack.reject(True)
        endpoint.reject.assert_called_with(message, True)