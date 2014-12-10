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

from logging import getLogger
from threading import local as Local

from uuid import uuid4

from gofer.messaging.adapter.url import URL
from gofer.messaging.adapter.factory import Adapter
from gofer.messaging.adapter.decorators import model
from gofer.messaging.model import ModelError, validate
from gofer.messaging import auth as auth


ROUTE_ALL = '#'
DIRECT = 'direct'
TOPIC = 'topic'
DEFAULT_URL = 'amqp://localhost'

log = getLogger(__name__)


# --- domain -----------------------------------------------------------------


class Model(object):

    @property
    def domain_id(self):
        raise NotImplementedError()


class _Domain(object):
    """
    Base domain container.
    """

    def __init__(self, builder=None):
        """
        :param builder: A factory method.
        :type builder: callable
        :return:
        """
        self.content = {}
        self.builder = builder

    def add(self, thing):
        """
        Add the object.
        :param thing: An object to be added.
        :type thing: Model
        """
        self.content[thing.domain_id] = thing

    def find(self, key):
        """
        Find the domain object by key.
        Returns the found object or the object created by the
        optional builder called as: builder(key).
        :param key: The object key.
        :type key: str
        :return: The requested object.
        :rtype: object
        """
        try:
            return self.content[key]
        except KeyError:
            pass
        if self.builder:
            return self.builder(key)

    def delete(self, thing):
        """
        Delete the specified node.
        :param thing: An object to be deleted.
        :type thing: Model
        """
        del self.content[thing.domain_id]

    def has(self, thing):
        """
        Test whether the thing is a member of the domain.
        :param thing: A thing to test.
        :type thing: Model
        :return: True if contained.
        :rtype: bool
        """
        return thing.domain_id in self.content

    def __contains__(self, thing):
        return self.has(thing)

    def __len__(self):
        return len(self.content)


# --- destination ------------------------------------------------------------


class Destination(Model):
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


# --- node -------------------------------------------------------------------


class Node(Model):
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

    @property
    def domain_id(self):
        """
        Get the domain ID.
        :return: The domain id.
        :rtype: str
        """
        return '::'.join((self.__class__.__name__, self.name))

    def declare(self, url):
        """
        Declare the node.
        :param url: The broker URL.
        :type url: str
        """
        raise NotImplementedError()

    def delete(self, url):
        """
        Delete the node.
        :param url: The broker URL.
        :type url: str
        """
        raise NotImplementedError()


class BaseExchange(Node):
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

    def __eq__(self, other):
        return isinstance(other, BaseExchange) and \
            self.name == other.name

    def __ne__(self, other):
        return not (self == other)


class Exchange(BaseExchange):

    def __init__(self, name, policy=None):
        """
        :param name: The exchange name.
        :type name: str
        :param policy: The routing policy (direct|topic|..).
        :type policy: str
        """
        BaseExchange.__init__(self, name, policy)

    @model
    def declare(self, url=None):
        """
        Declare the node.
        :param url: The broker URL.
        :type url: str
        :raise: ModelError
        """
        if self in Domain.external:
            # not managed
            return
        adapter = Adapter.find(url)
        impl = adapter.Exchange(self.name, policy=self.policy)
        impl.durable = self.durable
        impl.auto_delete = self.auto_delete
        impl.declare(url)

    @model
    def delete(self, url=None):
        """
        Delete the node.
        :param url: The broker URL.
        :type url: str
        :raise: ModelError
        """
        if self in Domain.external:
            # not managed
            return
        adapter = Adapter.find(url)
        impl = adapter.Exchange(self.name)
        impl.delete(url)


class BaseQueue(Node):
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

    def __init__(self, name, exchange, routing_key):
        """
        :param name: The queue name.
        :type name: str
        :param exchange: An AMQP exchange
        :type exchange: BaseExchange
        :param routing_key: Message routing key.
        :type routing_key: str
        """
        Node.__init__(self, name)
        self.exchange = exchange
        self.routing_key = routing_key
        self.durable = True
        self.auto_delete = False
        self.exclusive = False

    def destination(self, url):
        """
        Get a destination object for the node.
        :param url: The broker URL.
        :type url: str
        :return: A destination for the node.
        :rtype: Destination
        """
        raise NotImplementedError()

    def __eq__(self, other):
        return isinstance(other, BaseQueue) and \
            self.name == other.name

    def __ne__(self, other):
        return not (self == other)


class Queue(BaseQueue):
    """
    An AMQP message queue.
    """

    def __init__(self, name, exchange=None, routing_key=None):
        """
        :param name: The queue name.
        :type name: str
        :param exchange: An AMQP exchange
        :type exchange: BaseExchange
        :param routing_key: Message routing key.
        :type routing_key: str
        """
        BaseQueue.__init__(self, name, exchange, routing_key)

    @model
    def declare(self, url=None):
        """
        Declare the node.
        :param url: The broker URL.
        :type url: str
        :raise: ModelError
        """
        if self in Domain.external:
            # not managed
            return
        adapter = Adapter.find(url)
        impl = adapter.Queue(self.name, self.exchange, self.routing_key)
        impl.durable = self.durable
        impl.auto_delete = self.auto_delete
        impl.exclusive = self.exclusive
        impl.declare(url)

    @model
    def delete(self, url=None):
        """
        Delete the node.
        :param url: The broker URL.
        :type url: str
        :raise: ModelError
        """
        if self in Domain.external:
            # not managed
            return
        adapter = Adapter.find(url)
        impl = adapter.Queue(self.name)
        impl.delete(url)
        
    def destination(self, url):
        """
        Get a destination object for the node.
        :param url: The broker URL.
        :type url: str
        :return: A destination for the node.
        :rtype: Destination
        """
        adapter = Adapter.find(url)
        impl = adapter.Queue(self.name, self.exchange, self.routing_key)
        return impl.destination(url)

    @model
    def purge(self, url):
        """
        Purge (drain) all queued messages.
        :param url: The broker URL.
        :type url: str
        """
        reader = Reader(self, url=url)
        reader.open()
        try:
            while True:
                message = reader.get()
                if message:
                    message.ack()
                else:
                    break
        finally:
            reader.close()


# --- endpoint ---------------------------------------------------------------


class BaseEndpoint(Model):
    """
    Base class for an AMQP endpoint.
    :ivar url: The broker URL.
    :type url: str
    :ivar uuid: The endpoint UUID.
    :type uuid: str
    :ivar authenticator: A message authenticator.
    :type authenticator: gofer.messaging.auth.Authenticator
    """

    def __init__(self, url):
        """
        :param url: The broker url.
        :type url: str
        """
        self.url = url
        self.uuid = str(uuid4())
        self.authenticator = None

    def id(self):
        """
        Get the endpoint id
        :return: The id.
        :rtype: str
        """
        return self.uuid

    def is_open(self):
        """
        Get whether the endpoint has been opened.
        :return: True if open.
        :rtype bool
        """
        raise NotImplementedError()

    def channel(self):
        """
        Get a channel for the open connection.
        :return: An open channel.
        """
        raise NotImplementedError()

    def open(self):
        """
        Open and configure the endpoint.
        """
        raise NotImplementedError()

    def ack(self, message):
        """
        Ack the specified message.
        :param message: The message to acknowledge.
        """
        raise NotImplementedError()

    def reject(self, message, requeue=True):
        """
        Reject the specified message.
        :param message: The message to reject.
        :param requeue: Requeue the message or discard it.
        :type requeue: bool
        """
        raise NotImplementedError()

    def close(self, hard=False):
        """
        Close the endpoint.
        :param hard: Force the connection closed.
        :type hard: bool
        """
        raise NotImplementedError()

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *unused):
        self.close()


# --- messenger --------------------------------------------------------------


class Messenger(BaseEndpoint):
    """
    Provides AMQP messaging.
    """

    def endpoint(self):
        """
        Get the messenger endpoint.
        :return: An endpoint object.
        :rtype: BaseEndpoint
        """
        raise NotImplementedError()

    def is_open(self):
        """
        Get whether the messenger has been opened.
        :return: True if open.
        :rtype bool
        """
        return self.endpoint().is_open()

    def channel(self):
        """
        Get a channel for the open connection.
        :return: An open channel.
        """
        return self.endpoint().channel()

    def open(self):
        """
        Open and configure the endpoint.
        """
        self.endpoint().open()

    def close(self, hard=False):
        """
        Close the messenger.
        :param hard: Force the connection closed.
        :type hard: bool
        """
        self.endpoint().close(hard)


# --- reader -----------------------------------------------------------------


class Message(Model):
    """
    A read message.
    :ivar _reader: The reader that read the message.
    :type _reader: BaseReader
    :ivar _impl: The *real* message.
    :ivar _body: The *real* message body.
    :type _body: str
    """

    def __init__(self, reader, impl, body):
        """
        :ivar reader: The reader that read the message.
        :type reader: BaseReader
        :ivar impl: The *real* message.
        :ivar body: The *real* message body.
        :type body: str
        """
        self._reader = reader
        self._impl = impl
        self._body = body

    @property
    def body(self):
        """
        Get the message body.
        :return: The message body.
        :rtype: str
        """
        return self._body

    @model
    def ack(self):
        """
        Ack this message.
        :raise: ModelError
        """
        self._reader.ack(self._impl)

    @model
    def reject(self, requeue=True):
        """
        Reject this message.
        :param requeue: Requeue the message or discard it.
        :type requeue: bool
        :raise: ModelError
        """
        self._reader.reject(self._impl, requeue)

    def __str__(self):
        return str(self._body)


class BaseReader(Messenger):
    """
    An AMQP message reader.
    """

    def __init__(self, queue, url):
        """
        :param queue: The queue to consumer.
        :type queue: gofer.messaging.adapter.model.BaseQueue
        :param url: The broker url.
        :type url: str
        """
        Messenger.__init__(self, url)
        self.queue = queue

    def get(self, timeout=None):
        """
        Get the next *message* from the queue.
        :param timeout: The read timeout in seconds.
        :type timeout: int
        :return: The next message, or (None).
        :rtype: Message
        """
        raise NotImplementedError()

    def ack(self, message):
        """
        Ack the specified message.
        :param message: The message to acknowledge.
        """
        self.endpoint().ack(message)

    def reject(self, message, requeue=True):
        """
        Reject the specified message.
        :param message: The message to reject.
        :param requeue: Requeue the message or discard it.
        :type requeue: bool
        """
        self.endpoint().reject(message, requeue)


class Reader(BaseReader):
    """
    An AMQP queue reader.
    """

    def __init__(self, queue, url=None):
        """
        :param queue: The queue to consumer.
        :type queue: gofer.messaging.adapter.model.BaseQueue
        :param url: The broker url.
        :type url: str
        :see: gofer.messaging.adapter.url.URL
        """
        BaseReader.__init__(self, queue, url)
        adapter = Adapter.find(url)
        self._impl = adapter.Reader(queue, url)

    @model
    def channel(self):
        """
        Get a channel for the open connection.
        :return: An open channel.
        :raise: ModelError
        """
        return self._impl.channel()

    @model
    def open(self):
        """
        Open the reader.
        :raise: ModelError
        """
        self._impl.open()

    @model
    def ack(self, message):
        """
        Ack the specified message.
        :param message: The message to acknowledge.
        :type message: Message
        :raise: ModelError
        """
        message.ack()

    @model
    def reject(self, message, requeue=True):
        """
        Reject the specified message.
        :param message: The message to reject.
        :type message: Message
        :param requeue: Requeue the message or discard it.
        :type requeue: bool
        :raise: ModelError
        """
        message.reject(requeue)

    @model
    def close(self, hard=False):
        """
        Close the reader.
        :param hard: Force the connection closed.
        :type hard: bool
        :raise: ModelError
        """
        self._impl.close(hard)

    @model
    def get(self, timeout=None):
        """
        Get the next message.
        :param timeout: The read timeout in seconds.
        :type timeout: int
        :return: The next message, or (None).
        :raise: ModelError
        """
        return self._impl.get(timeout)

    @model
    def next(self, timeout=90):
        """
        Get the next valid *document* from the queue.
        :param timeout: The read timeout in seconds.
        :type timeout: int
        :return: The next document.
        :rtype: tuple: (Message, Document)
        :raises: model.InvalidDocument
        """
        message = self.get(timeout)
        if message:
            try:
                document = auth.validate(self.authenticator, message.body)
                validate(document)
            except ModelError:
                message.ack()
                raise
            log.debug('read next: %s', document)
            return message, document
        else:
            return None, None

    @model
    def search(self, sn, timeout=90):
        """
        Search for a document by serial number.
        :param sn: A serial number.
        :type sn: str
        :param timeout: The read timeout.
        :type timeout: int
        :return: The matched document.
        :rtype: Document
        :raise: ModelError
        """
        while True:
            message, document = self.next(timeout)
            if message:
                message.ack()
            else:
                return
            if sn == document.sn:
                # matched
                return document
            else:
                # discarded
                continue


# --- producer ---------------------------------------------------------------


class BaseProducer(Messenger):
    """
    An AMQP message producer.
    """

    def send(self, destination, ttl, **body):
        """
        Send a message.
        :param destination: An AMQP destination.
        :type destination: Destination
        :param ttl: Time to Live (seconds)
        :type ttl: float
        :keyword body: document body.
        :return: The message serial number.
        :rtype: str
        """
        raise NotImplementedError()

    def broadcast(self, destinations, ttl, **body):
        """
        Send a message to multiple destinations.
        :param destinations: A list of: Destination
        :type destinations: list
        :param ttl: Time to Live (seconds)
        :type ttl: float
        :keyword body: document body.
        :return: A list of (destination, sn).
        :rtype: list
        """
        raise NotImplementedError()


class Producer(BaseProducer):
    """
    An AMQP message producer.
    """

    def __init__(self, url=None):
        """
        :param url: The broker url.
        :type url: str
        """
        BaseProducer.__init__(self, url)
        adapter = Adapter.find(url)
        self._impl = adapter.Producer(url)

    @model
    def channel(self):
        """
        Get a channel for the open connection.
        :return: An open channel.
        :raise: ModelError
        """
        return self._impl.channel()

    @model
    def open(self):
        """
        Open the producer.
        :raise: ModelError
        """
        self._impl.open()

    @model
    def close(self, hard=False):
        """
        Close the producer.
        :param hard: Force the connection closed.
        :type hard: bool
        :raise: ModelError
        """
        self._impl.close(hard)

    @model
    def send(self, destination, ttl=None, **body):
        """
        Send a message.
        :param destination: An AMQP destination.
        :type destination: Destination
        :param ttl: Time to Live (seconds)
        :type ttl: float
        :keyword body: document body.
        :return: The message serial number.
        :rtype: str
        :raise: ModelError
        """
        self._impl.authenticator = self.authenticator
        return self._impl.send(destination, ttl, **body)

    @model
    def broadcast(self, destinations, ttl=None, **body):
        """
        Send a message to multiple destinations.
        :param destinations: A list of: Destination
        :type destinations: list
        :param ttl: Time to Live (seconds)
        :type ttl: float
        :keyword body: document body.
        :return: A list of (destination, sn).
        :rtype: list
        :raise: ModelError
        """
        self._impl.authenticator = self.authenticator
        return self._impl.broadcast(destinations, ttl, **body)


class BasePlainProducer(Messenger):
    """
    An plain AMQP message producer.
    """

    def send(self, destination, content, ttl=None):
        """
        Send a message.
        :param destination: An AMQP destination.
        :type destination: Destination
        :param content: The message content
        :type content: buf
        :param ttl: Time to Live (seconds)
        :type ttl: float
        :return: A message_id.
        :rtype: str
        """
        raise NotImplementedError()

    def broadcast(self, destinations, content, ttl=None):
        """
        Send a message to multiple destinations.
        :param destinations: A list of: Destination
        :type destinations: list
        :param content: The message content
        :type content: buf
        :return: A list of message_id
        :rtype: list
        """
        raise NotImplementedError()


class PlainProducer(BasePlainProducer):
    """
    An plain AMQP message producer.
    """

    def __init__(self, url=None):
        """
        :param url: The broker url.
        :type url: str
        """
        BasePlainProducer.__init__(self, url)
        adapter = Adapter.find(url)
        self._impl = adapter.PlainProducer(url)

    @model
    def channel(self):
        """
        Get a channel for the open connection.
        :return: An open channel.
        :raise: ModelError
        """
        return self._impl.channel()

    @model
    def open(self):
        """
        Open the producer.
        :raise: ModelError
        """
        self._impl.open()

    @model
    def close(self, hard=False):
        """
        Close the producer.
        :param hard: Force the connection closed.
        :type hard: bool
        :raise: ModelError
        """
        self._impl.close(hard)

    @model
    def send(self, destination, content, ttl=None):
        """
        Send a message.
        :param destination: An AMQP destination.
        :type destination: Destination
        :param content: The message content
        :type content: buf
        :param ttl: Time to Live (seconds)
        :type ttl: float
        :return: A message_id.
        :rtype: str
        :raise: ModelError
        """
        self._impl.authenticator = self.authenticator
        return self._impl.send(destination, content, ttl)

    @model
    def broadcast(self, destinations, content, ttl=None):
        """
        Send a message to multiple destinations.
        :param destinations: A list of: Destination
        :type destinations: list
        :param content: The message content
        :type content: buf
        :return: A list of message_id
        :rtype: list
        :raise: ModelError
        """
        self._impl.authenticator = self.authenticator
        return self._impl.broadcast(destinations, content, ttl)


# --- connection -------------------------------------------------------------


class BaseConnection(Model):
    """
    Base AMQP connection.
    :ivar url: A broker URL.
    :type url: str
    """

    def __init__(self, url):
        """
        :param url: A broker URL.
        :type url: str
        :see: URL
        """
        self.url = url

    def is_open(self):
        """
        Get whether the connection has been opened.
        :return: True if open.
        :rtype bool
        """
        raise NotImplementedError()

    def open(self):
        """
        Open a connection.
        """
        raise NotImplementedError()

    def channel(self):
        """
        Open a channel.
        :return: The open channel.
        """
        raise NotImplementedError()

    def close(self, hard=False):
        """
        Close the connection.
        :param hard: Force the connection closed.
        :type hard: bool
        """
        raise NotImplementedError()

    def __str__(self):
        return str(self.url)

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *unused):
        self.close()


class Connection(BaseConnection):
    """
    An AMQP channel object.
    """

    def __init__(self, url=None):
        BaseConnection.__init__(self, url)
        adapter = Adapter.find(url)
        self._impl = adapter.Connection(url)

    def is_open(self):
        """
        Get whether the connection has been opened.
        :return: True if open.
        :rtype bool
        """
        return self._impl.is_open()

    @model
    def open(self):
        """
        Open the connection.
        :raise: ModelError
        """
        self._impl.open()

    @model
    def channel(self):
        """
        Open a channel.
        :return The *real* channel.
        :raise: ModelError
        """
        return self._impl.channel()

    @model
    def close(self, hard=False):
        """
        Close the connection.
        :param hard: Force the connection closed.
        :type hard: bool
        :raise: ModelError
        """
        self._impl.close(hard)


class SharedConnection(type):
    """
    Thread local shared connection metaclass.
    Usage: __metaclass__ = SharedConnection
    """

    def __init__(cls, what, bases, _dict):
        super(SharedConnection, cls).__init__(what, bases, _dict)
        cls.local = Local()

    @property
    def connections(self):
        try:
            return self.local.d
        except AttributeError:
            d = {}
            self.local.d = d
            return d

    def __call__(cls, url):
        try:
            return cls.connections[url]
        except KeyError:
            inst = super(SharedConnection, cls).__call__(url)
            cls.connections[url] = inst
            return inst


# --- broker -----------------------------------------------------------------


class SSL(Model):
    """
    SSL configuration.
    :ivar ca_certificate: The absolute path to a CA certificate.
    :type ca_certificate: str
    :ivar client_key: The absolute path to a client key.
    :type client_key: str
    :ivar client_certificate: The absolute path to a client certificate.
    :type client_certificate: str
    :ivar host_validation: Do SSL host validation.
    :type host_validation: bool
    """

    def __init__(self):
        self.ca_certificate = None
        self.client_key = None
        self.client_certificate = None
        self.host_validation = False

    def __str__(self):
        s = list()
        s.append('ca: %s' % self.ca_certificate)
        s.append('key: %s' % self.client_key)
        s.append('certificate: %s' % self.client_certificate)
        s.append('host-validation: %s' % self.host_validation)
        return '|'.join(s)


class Broker(Model):
    """
    Represents an AMQP broker.
    :ivar url: The broker's url.
    :type url: URL
    :ivar ssl: The SSL configuration.
    :type ssl: SSL
    """

    def __init__(self, url=None):
        """
        :param url: The broker url:
            <adapter>+<scheme>://<userid:password@<host>:<port>/<virtual-host>.
        :type url: str
        """
        self.url = URL(url or DEFAULT_URL)
        self.ssl = SSL()

    @property
    def domain_id(self):
        """
        Get the domain ID.
        :return: The domain id.
        :rtype: str
        """
        return str(self.url)

    @property
    def adapter(self):
        """
        Get the (gofer) adapter component of the url.
        :return: The adapter component.
        :rtype: str
        """
        return self.url.adapter

    @property
    def scheme(self):
        """
        Get the scheme component of the url.
        :return: The scheme component.
        :rtype: str
        """
        return self.url.scheme

    @property
    def host(self):
        """
        Get the host component of the url.
        :return: The host component.
        :rtype: str
        """
        return self.url.host

    @property
    def port(self):
        """
        Get the port component of the url.
        :return: The port component.
        :rtype: str
        """
        return self.url.port

    @property
    def userid(self):
        """
        Get the userid component of the url.
        :return: The userid component.
        :rtype: str
        """
        return self.url.userid

    @property
    def password(self):
        """
        Get the password component of the url.
        :return: The password component.
        :rtype: str
        """
        return self.url.password

    @property
    def virtual_host(self):
        """
        Get the virtual_host component of the url.
        :return: The virtual_host component.
        :rtype: str
        """
        return self.url.path

    def __str__(self):
        s = list()
        s.append('URL: %s' % self.url)
        s.append('SSL: %s' % self.ssl)
        return '|'.join(s)


# --- doamin -----------------------------------------------------------------


class Domain(object):
    """
    Model object domains.
    :cvar broker: Collection of brokers.
    :type broker: Domain
    :cvar external: External (not managed) nodes.
    :type external: Domain
    """
    broker = _Domain(Broker)
    external = _Domain()
