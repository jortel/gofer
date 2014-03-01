# Copyright (c) 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from gofer.transport.factory import Transport as _Transport
from gofer.transport.consumer import Consumer as BaseConsumer
from gofer.transport.model import Destination as BaseDestination


# --- utils ------------------------------------------------------------------


def Transport(thing):
    """
    Ensure *thing* is a transport object.
    :param thing: A transport object or package name.
    :type thing: (str|Transport)
    :return: A transport object.
    :rtype: _Transport
    """
    if isinstance(thing, _Transport):
        return thing
    if isinstance(thing, str):
        return _Transport(thing)
    if thing is None:
        return _Transport(thing)
    raise ValueError('must be (str|Transport)')


# --- metaclasses ------------------------------------------------------------


class _Broker:

    def __init__(self, *unused):
        pass

    def __call__(self, url=None, transport=None):
        tp = Transport(transport)
        return tp.broker(url)


class _Exchange:

    @staticmethod
    def direct(transport=None):
        tp = Transport(transport)
        return tp.plugin.Exchange.direct()

    @staticmethod
    def topic(transport=None):
        tp = Transport(transport)
        return tp.plugin.Exchange.topic()

    def __init__(self, *unused):
        pass

    def __call__(self, name, policy=None, transport=None):
        tp = Transport(transport)
        return tp.exchange(name, policy=policy)


class _Queue:

    def __init__(self, *unused):
        pass

    def __call__(self, name, exchange=None, routing_key=None, transport=None):
        tp = Transport(transport)
        return tp.queue(name, exchange=exchange, routing_key=routing_key)


class _Producer:

    def __init__(self, *unused):
        pass

    def __call__(self, uuid=None, url=None, transport=None):
        tp = Transport(transport)
        return tp.producer(url, uuid=uuid)


class _BinaryProducer:

    def __init__(self, *unused):
        pass

    def __call__(self, uuid=None, url=None, transport=None):
        tp = Transport(transport)
        return tp.binary_producer(url, uuid=uuid)


class _Reader:
    def __init__(self, *unused):
        pass

    def __call__(self, queue, uuid=None, url=None, transport=None):
        tp = Transport(transport)
        return tp.reader(url, queue, uuid=uuid)


# --- API classes ------------------------------------------------------------


class Broker(object):
    """
    An AMQP message broker.
    """

    __metaclass__ = _Broker

    def __init__(self, url=None, transport=None):
        """
        :param url: The broker URL.
        :type url: str
        :param transport: An AMQP transport.
        :type transport: (str|gofer.transport.Transport)
        :see: gofer.transport.broker.Broker
        """


class Exchange(object):
    """
    An AMQP exchange.
    """

    __metaclass__ = _Exchange

    def __init__(self, name, policy=None, transport=None):
        """
        :param name: The exchange name.
        :type name: str
        :param policy: The routing policy (direct|topic).
        :type policy: str
        :param transport: An AMQP transport.
        :type transport: (str|gofer.transport.Transport)
        :see: gofer.transport.broker.Exchange
        """

    def declare(self, url=None):
        """
        Declare the exchange.
        :param url: The broker URL.
        :type url: str
        """

    def delete(self, url=None):
        """
        Declare the exchange.
        :param url: The broker URL.
        :type url: str
        """


class Queue(object):
    """
    An AMQP message queue.
    """

    __metaclass__ = _Queue

    def __init__(self, name, exchange=None, routing_key=None, transport=None):
        """.
        :param name: The topic name.
        :param name: str
        :param exchange: An AMQP exchange.
        :param exchange: str
        :param routing_key: An AMQP routing key.
        :type routing_key: str
        :param transport: An AMQP transport.
        :type transport: (str|gofer.transport.Transport)
        :see: gofer.transport.node.Queue.
        """

    def destination(self):
        """
        Get a destination object for the node.
        :return: A destination for the node.
        :rtype: Destination
        """

    def declare(self, url=None):
        """
        Declare the exchange.
        :param url: The broker URL.
        :type url: str
        """

    def delete(self, url=None):
        """
        Declare the exchange.
        :param url: The broker URL.
        :type url: str
        """


class Producer(object):
    """
    An AMQP message producer.
    """

    __metaclass__ = _Producer

    def __init__(self, uuid=None, url=None, transport=None):
        """
        :param uuid: The (optional) producer ID.
        :type uuid: str
        :param url: The broker URL.
        :type url: str
        :param transport: An AMQP transport.
        :type transport: (str|gofer.transport.Transport)
        """

    def send(self, destination, ttl=None, **body):
        """
        Send a message.
        :param destination: An AMQP destination.
        :type destination: gofer.transport.model.Destination
        :param ttl: Time to Live (seconds)
        :type ttl: float
        :keyword body: document body.
        :return: The message serial number.
        :rtype: str
        """

    def broadcast(self, destinations, **body):
        """
        Broadcast a message to (N) queues.
        :param destinations: A list of AMQP destinations.
        :type destinations: [gofer.transport.node.Destination,..]
        :keyword body: document body.
        :return: A list of serial numbers.
        :rtype: list
        """

    def close(self):
        """
        Implemented by the object provided by the transport.
        """


class BinaryProducer(object):
    """
    An AMQP message producer.
    """

    __metaclass__ = _BinaryProducer

    def __init__(self, uuid=None, url=None, transport=None):
        """
        :param uuid: The (optional) producer ID.
        :type uuid: str
        :param url: The broker URL.
        :type url: str
        :param transport: An AMQP transport.
        :type transport: (str|gofer.transport.Transport)
        """

    def send(self, destination, content, ttl=None):
        """
        Send a message.
        :param destination: An AMQP destination.
        :type destination: gofer.transport.model.Destination
        :type content: The message body.
        :type content: str
        :param ttl: Time to Live (seconds)
        :type ttl: float
        :return: The message serial number.
        :rtype: str
        """

    def broadcast(self, destinations, **body):
        """
        Broadcast a message to (N) queues.
        :param destinations: A list of AMQP destinations.
        :type destinations: [gofer.transport.node.Destination,..]
        :type content: The message body.
        :type content: str
        :param ttl: Time to Live (seconds)
        :type ttl: float
        :return: A list of serial numbers.
        :rtype: list
        """

    def close(self):
        """
        Implemented by the object provided by the transport.
        """


class Reader(object):
    """
    An AMQP message reader.
    """

    __metaclass__ = _Reader

    def __init__(self, queue, uuid=None, url=None, transport=None):
        """
        :param queue: The AMQP node.
        :type queue: gofer.transport.model.Queue
        :param uuid: The (optional) producer ID.
        :type uuid: str
        :param transport: An AMQP transport.
        :type transport: (str|gofer.transport.Transport)
        """

    def next(self, timeout=None):
        """
        Get the next document from the queue.
        :param timeout: The read timeout in seconds.
        :type timeout: int
        :return: A tuple of: (document, ack())
        :rtype: (Document, callable)
        """

    def search(self, sn, timeout=None):
        """
        Search the reply queue for the document with the matching serial #.
        :param sn: The expected serial number.
        :type sn: str
        :param timeout: The read timeout.
        :type timeout: int
        :return: The next document.
        :rtype: Document
        """

    def close(self):
        """
        Implemented by the object provided by the transport.
        """


class Consumer(BaseConsumer):
    """
    An AMQP consumer.
    Thread used to consumer messages from the specified queue.
    On receipt, each message is used to build an document
    and passed to dispatch().
    """

    def __init__(self, queue, url=None, transport=None):
        """
        :param queue: The AMQP node.
        :type queue: gofer.transport.model.Queue
        :param url: The broker URL.
        :type url: str
        :param transport: An AMQP transport.
        :type transport: (str|gofer.transport.Transport)
        """
        tp = Transport(transport)
        BaseConsumer.__init__(self, tp.reader(url, queue))
        self.url = url
        self.queue = queue
        self.transport = tp


class Destination(BaseDestination):
    pass