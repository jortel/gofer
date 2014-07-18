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

from gofer.transport.binder import Binder


# routing key
ROUTE_ALL = '#'

# exchange types
DIRECT = 'direct'
TOPIC = 'topic'


class Node(object):
    """
    An AMQP node.
    :ivar name: The node name.
    :type name: str
    """

    def __init__(self, name):
        """
        :param name: The node name.
        :type name: str
        """
        self.name = name

    def declare(self, url):
        """
        Declare the node.
        :param url: The peer URL.
        :type url: str
        :return: self
        """
        pass

    def delete(self, url):
        """
        Delete the node.
        :param url: The peer URL.
        :type url: str
        :return: self
        """
        pass


class Exchange(Node):
    """
    An AMQP exchange.
    :ivar policy: The routing policy (direct|topic|..).
    :type policy: str
    :ivar durable: Indicates the exchange is durable.
    :type durable: bool
    :ivar auto_delete: The exchange is auto deleted.
    :type auto_delete: bool
    """

    def __init__(self, name, policy=None):
        """
        :param name: The exchange name.
        :type name: str
        :param policy: The routing policy (direct|topic|..).
        :type policy: str
        """
        Node.__init__(self, name)
        self.policy = policy
        self.durable = True
        self.auto_delete = False

    def declare(self, url):
        """
        Declare the node.
        :param url: The peer URL.
        :type url: str
        :return: self
        """
        plugin = Binder.find(url)
        impl = plugin.Exchange(self.name, policy=self.policy)
        impl.durable = self.durable
        impl.auto_delete = self.auto_delete
        impl.declare(url)

    def delete(self, url):
        """
        Delete the node.
        :param url: The peer URL.
        :type url: str
        :return: self
        """
        plugin = Binder.find(url)
        impl = plugin.Exchange(self.name)
        impl.delete(url)

    def __eq__(self, other):
        return isinstance(other, Exchange) and \
            self.name == other.name

    def __ne__(self, other):
        return not (self == other)


class Destination(object):
    """
    An AMQP destination.
    :ivar routing_key: Message routing key.
    :type routing_key: str
    :ivar exchange: An (optional) AMQP exchange.
    :type exchange: str
    """

    ROUTING_KEY = 'routing_key'
    EXCHANGE = 'exchange'

    @staticmethod
    def create(d):
        return Destination(d[Destination.ROUTING_KEY], d[Destination.EXCHANGE])

    def __init__(self, routing_key, exchange=''):
        """
        :param exchange: An AMQP exchange.
        :type exchange: str
        :param routing_key: Message routing key.
        :type routing_key: str
        """
        self.routing_key = routing_key
        self.exchange = exchange

    def dict(self):
        return {
            Destination.ROUTING_KEY: self.routing_key,
            Destination.EXCHANGE: self.exchange,
        }

    def __eq__(self, other):
        return isinstance(other, Destination) and \
            self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not (self == other)

    def __str__(self):
        return str(self.__dict__)

    def __repr__(self):
        return repr(self.__dict__)


class Queue(Node):
    """
    An AMQP queue.
    :ivar exchange: An AMQP exchange.
    :type exchange: Exchange
    :ivar routing_key: Message routing key.
    :type routing_key: str
    :ivar durable: Indicates the queue is durable.
    :type durable: bool
    :ivar auto_delete: The queue is auto deleted.
    :type auto_delete: bool
    :ivar exclusive: Indicates the queue can only have one consumer.
    :type exclusive: bool
    """

    def __init__(self, name, exchange=None, routing_key=None):
        """
        :param name: The queue name.
        :type name: str
        :param exchange: An AMQP exchange
        :type exchange: Exchange
        :param routing_key: Message routing key.
        :type routing_key: str
        """
        Node.__init__(self, name)
        self.exchange = exchange
        self.routing_key = routing_key
        self.durable = True
        self.auto_delete = False
        self.exclusive = False

    def destination(self):
        """
        Get a destination object for the node.
        :return: A destination for the node.
        :rtype: Destination
        """
        return Destination(self.routing_key, exchange=self.exchange.name)

    def declare(self, url):
        """
        Declare the node.
        :param url: The peer URL.
        :type url: str
        :return: self
        """
        plugin = Binder.find(url)
        impl = plugin.Queue(self.name, exchange=self.exchange, routing_key=self.routing_key)
        impl.durable = self.durable
        impl.auto_delete = self.auto_delete
        impl.exclusive = self.exclusive
        impl.declare(url)

    def delete(self, url):
        """
        Delete the node.
        :param url: The peer URL.
        :type url: str
        :return: self
        """
        plugin = Binder.find(url)
        impl = plugin.Queue(self.name)
        impl.delete(url)

    def __eq__(self, other):
        return isinstance(other, Queue) and \
            self.name == other.name

    def __ne__(self, other):
        return not (self == other)


class Reader(object):
    """
    An AMQP message reader.
    """

    def __init__(self, queue, uuid=None, url=None):
        """
        :param queue: The queue to consumer.
        :type queue: gofer.transport.qpid.model.Queue
        :param uuid: The endpoint uuid.
        :type uuid: str
        :param url: The broker url <transport>://<user>:<pass>@<host>:<port>/<virtual-host>.
        :type url: str
        """
        self.queue = queue
        self.uuid = uuid
        self.url = url
        plugin = Binder.find(url)
        self._impl = plugin.Reader(queue, uuid=uuid, url=url)

    def open(self):
        """
        Open the reader.
        """
        self._impl.open()

    def close(self):
        """
        Close the reader.
        """
        self._impl.close()

    def get(self, timeout=None):
        """
        Get the next message.
        :param timeout: The read timeout.
        :type timeout: int
        :return: The next message, or (None).
        """
        return self._impl.get(timeout)

    def next(self, timeout=90):
        """
        Get the next document from the queue.
        :param timeout: The read timeout.
        :type timeout: int
        :return: A tuple of: (document, ack())
        :rtype: (Document, callable)
        :raises: model.InvalidDocument
        """
        return self._impl.next(timeout)

    def search(self, sn, timeout=90):
        """
        Search the reply queue for the document with the matching serial #.
        :param sn: The expected serial number.
        :type sn: str
        :param timeout: The read timeout.
        :type timeout: int
        :return: The next document.
        :rtype: Document
        """
        return self._impl.search(sn, timeout)


class Producer(object):
    """
    An AMQP (message producer.
    """

    def __init__(self, uuid=None, url=None):
        """
        :param uuid: The endpoint uuid.
        :type uuid: str
        :param url: The broker url <transport>://<user>:<pass>@<host>:<port>/<virtual-host>.
        :type url: str
        """
        self.uuid = uuid
        self.url = url
        plugin = Binder.find(url)
        self._impl = plugin.Producer(uuid=uuid, url=uuid)

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
        self._impl.send(destination, ttl=ttl, **body)

    def broadcast(self, destinations, ttl=None, **body):
        """
        Broadcast a message to (N) queues.
        :param destinations: A list of AMQP destinations.
        :type destinations: [gofer.transport.node.Node,..]
        :param ttl: Time to Live (seconds)
        :type ttl: float
        :keyword body: document body.
        :return: A list of (addr,sn).
        :rtype: list
        """
        self._impl.broadcast(destinations, ttl=ttl, **body)


class BinaryProducer(object):
    """
    An binary AMQP message producer.
    """

    def __init__(self, uuid=None, url=None):
        """
        :param uuid: The endpoint uuid.
        :type uuid: str
        :param url: The broker url <transport>://<user>:<pass>@<host>:<port>/<virtual-host>.
        :type url: str
        """
        self.uuid = uuid
        self.url = url
        plugin = Binder.find(url)
        self._impl = plugin.BinaryProducer(uuid=uuid, url=url)

    def send(self, destination, content, ttl=None):
        """
        Send a message.
        :param destination: An AMQP destination.
        :type destination: gofer.transport.model.Destination
        :param content: The message content
        :type content: buf
        :param ttl: Time to Live (seconds)
        :type ttl: float
        """
        self._impl.send(destination, content, ttl=ttl)

    def broadcast(self, destinations, content, ttl=None):
        """
        Broadcast a message to (N) queues.
        :param destinations: A list of AMQP destinations.
        :type destinations: [gofer.transport.node.Node,..]
        :param content: The message content
        :type content: buf
        """
        self._impl.send(destinations, content, ttl=ttl)
