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

from gofer.transport.factory import Transport
from gofer.transport.consumer import Consumer as BaseConsumer
from gofer.transport.model import Destination as BaseDestination


# --- metaclasses ------------------------------------------------------------


class _Broker:

    def __init__(self, *unused):
        pass

    def __call__(self, url=None):
        tp = Transport(url)
        return tp.broker()


class _Exchange:

    @staticmethod
    def direct(url=None):
        tp = Transport(url)
        return tp.Exchange.direct()

    @staticmethod
    def topic(url=None):
        tp = Transport(url)
        return tp.Exchange.topic()

    def __init__(self, *unused):
        pass

    def __call__(self, name, policy=None, url=None):
        tp = Transport(url)
        return tp.exchange(name, policy=policy)


class _Queue:

    def __init__(self, *unused):
        pass

    def __call__(self, name, exchange=None, routing_key=None, url=None):
        tp = Transport(url)
        return tp.queue(name, exchange=exchange, routing_key=routing_key)


class _Producer:

    def __init__(self, *unused):
        pass

    def __call__(self, uuid=None, url=None):
        tp = Transport(url)
        return tp.producer(uuid=uuid)


class _BinaryProducer:

    def __init__(self, *unused):
        pass

    def __call__(self, uuid=None, url=None):
        tp = Transport(url)
        return tp.binary_producer(uuid=uuid)


class _Reader:
    def __init__(self, *unused):
        pass

    def __call__(self, queue, uuid=None, url=None):
        tp = Transport(url)
        return tp.reader(queue, uuid=uuid)


# --- API classes ------------------------------------------------------------


class Broker(object):
    """
    An AMQP message broker.
    """

    __metaclass__ = _Broker

    def __init__(self, url=None):
        """
        :param url: The broker URL.
        :type url: str
        :see: gofer.transport.broker.Broker
        """


class Exchange(object):
    """
    An AMQP exchange.
    """

    __metaclass__ = _Exchange

    def __init__(self, name, policy=None, url=None):
        """
        :param name: The exchange name.
        :type name: str
        :param policy: The routing policy (direct|topic).
        :type policy: str
        :param url: The broker URL.
        :type url: str
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

    def __init__(self, name, exchange=None, routing_key=None, url=None):
        """.
        :param name: The topic name.
        :param name: str
        :param exchange: An AMQP exchange.
        :param exchange: str
        :param routing_key: An AMQP routing key.
        :type routing_key: str
        :param url: The broker URL.
        :type url: str
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

    def __init__(self, uuid=None, url=None):
        """
        :param uuid: The (optional) producer ID.
        :type uuid: str
        :param url: The broker URL.
        :type url: str
        """

    def send(self, destination, ttl=None, **body):
        """
        Send a message.
        :param destination: An AMQP destination.
        :type destination: gofer.transport.model.Destination
        :param ttl: Time to Live (seconds)
        :type ttl: float
        :keyword body: envelope body.
        :return: The message serial number.
        :rtype: str
        """

    def broadcast(self, destinations, **body):
        """
        Broadcast a message to (N) queues.
        :param destinations: A list of AMQP destinations.
        :type destinations: [gofer.transport.node.Destination,..]
        :keyword body: envelope body.
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

    def __init__(self, uuid=None, url=None):
        """
        :param uuid: The (optional) producer ID.
        :type uuid: str
        :param url: The broker URL.
        :type url: str
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

    def __init__(self, queue, uuid=None, url=None):
        """
        :param queue: The AMQP node.
        :type queue: gofer.transport.model.Queue
        :param uuid: The (optional) producer ID.
        :type uuid: str
        """

    def next(self, timeout=None):
        """
        Get the next envelope from the queue.
        :param timeout: The read timeout in seconds.
        :type timeout: int
        :return: A tuple of: (envelope, ack())
        :rtype: (Envelope, callable)
        """

    def search(self, sn, timeout=None):
        """
        Search the reply queue for the envelope with the matching serial #.
        :param sn: The expected serial number.
        :type sn: str
        :param timeout: The read timeout.
        :type timeout: int
        :return: The next envelope.
        :rtype: Envelope
        """

    def close(self):
        """
        Implemented by the object provided by the transport.
        """


class Consumer(BaseConsumer):
    """
    An AMQP consumer.
    Thread used to consumer messages from the specified queue.
    On receipt, each message is used to build an envelope
    and passed to dispatch().
    """

    def __init__(self, queue, url=None):
        """
        :param queue: The AMQP node.
        :type queue: gofer.transport.model.Queue
        :param uuid: The (optional) producer ID.
        :type uuid: str
        """
        tp = Transport(url)
        BaseConsumer.__init__(self, tp.reader(queue))
        self.url = url
        self.queue = queue

    def dispatch(self, envelope):
        pass


class Destination(BaseDestination):
    pass