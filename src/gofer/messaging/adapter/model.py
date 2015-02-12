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

from uuid import uuid4

from gofer.messaging.model import VERSION, Document
from gofer.messaging.adapter.url import URL
from gofer.messaging.adapter.factory import Adapter
from gofer.messaging.model import ModelError, validate
from gofer.messaging import auth as auth


ROUTE_ALL = '#'
DIRECT = 'direct'
TOPIC = 'topic'
DEFAULT_URL = 'amqp://localhost'

log = getLogger(__name__)


def model(fn):
    def _fn(*args, **keywords):
        try:
            return fn(*args, **keywords)
        except ModelError:
            raise
        except Exception, e:
            log.exception(str(e))
            raise ModelError(*e.args)
    return _fn


# --- model ------------------------------------------------------------------


class NotFound(ModelError):
    """
    Model object not found.
    """


class Model(object):
    """
    Adapter model object.
    """

    @property
    def domain_id(self):
        """
        Unique domain ID.
        :return: A unique domain ID.
        :rtype: str
        """
        return '::'.join((self.__class__.__name__, str(id(self))))


class _Domain(object):
    """
    Base domain container.
    """

    def __init__(self):
        self.content = {}

    def add(self, model):
        """
        Add the domain object.
        :param model: A model object to be added.
        :type model: Model
        """
        self.content[model.domain_id] = model

    def find(self, domain_id):
        """
        Find an object by domain_id.
        :param domain_id: The domain ID.
        :type domain_id: str
        :return: The requested object.
        :raise: NotFound
        """
        try:
            return self.content[domain_id]
        except KeyError:
            raise NotFound(domain_id)

    def delete(self, thing):
        """
        Delete the specified node.
        :param thing: An object to be deleted.
        :type thing: Model
        """
        del self.content[thing.domain_id]

    def contains(self, thing):
        """
        Test whether the thing is a member of the domain.
        :param thing: A thing to test.
        :type thing: Model
        :return: True if contained.
        :rtype: bool
        """
        return thing.domain_id in self.content

    def __contains__(self, thing):
        return self.contains(thing)

    def __len__(self):
        return len(self.content)


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

    def __str__(self):
        return self.name
    

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

    def __init__(self, name, policy=DIRECT):
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

    def bind(self, queue, url):
        """
        Bind the specified queue.
        :param queue: The queue to bind.
        :type queue: BaseQueue
        :param url: The broker URL.
        :type url: str
        """
        raise NotImplementedError()

    def unbind(self, queue, url):
        """
        Unbind the specified queue.
        :param queue: The queue to unbind.
        :type queue: BaseQueue
        :param url: The broker URL.
        :type url: str
        """
        raise NotImplementedError()

    def __eq__(self, other):
        return isinstance(other, BaseExchange) and \
            self.name == other.name

    def __ne__(self, other):
        return not (self == other)


class Exchange(BaseExchange):

    def __init__(self, name, policy=DIRECT, url=None):
        """
        :param name: The exchange name.
        :type name: str
        :param policy: The routing policy (direct|topic|..).
        :type policy: str
        :param url: The (optional) broker URL.
        :type url: str
        """
        BaseExchange.__init__(self, name, policy)
        self.url = url

    @model
    def declare(self, url=None):
        """
        Declare the exchange.
        :param url: The broker URL.
        :type url: str
        :raise: ModelError
        """
        url = url or self.url
        adapter = Adapter.find(url)
        impl = adapter.Exchange(self.name, self.policy)
        impl.durable = self.durable
        impl.auto_delete = self.auto_delete
        impl.declare(url)

    @model
    def delete(self, url=None):
        """
        Delete the exchange.
        :param url: The broker URL.
        :type url: str
        :raise: ModelError
        """
        url = url or self.url
        adapter = Adapter.find(url)
        impl = adapter.Exchange(self.name, self.policy)
        impl.delete(url)

    @model
    def bind(self, queue, url=None):
        """
        Bind the specified queue.
        :param queue: The queue to bind.
        :type queue: BaseQueue
        :param url: The broker URL.
        :type url: str
        """
        url = url or self.url
        adapter = Adapter.find(url)
        impl = adapter.Exchange(self.name, self.policy)
        impl.bind(queue, url)

    @model
    def unbind(self, queue, url=None):
        """
        Unbind the specified queue.
        :param queue: The queue to unbind.
        :type queue: BaseQueue
        :param url: The broker URL.
        :type url: str
        """
        url = url or self.url
        adapter = Adapter.find(url)
        impl = adapter.Exchange(self.name, self.policy)
        impl.unbind(queue, url)


class BaseQueue(Node):
    """
    An AMQP queue.
    :ivar durable: Indicates the queue is durable.
    :type durable: bool
    :ivar auto_delete: The queue is auto deleted.
    :type auto_delete: bool
    :ivar expiration: The auto delete expiration (seconds).
    :type expiration: int
    :ivar exclusive: Indicates the queue can only have one consumer.
    :type exclusive: bool
    """

    def __init__(self, name):
        """
        :param name: The queue name.
        :type name: str
        """
        Node.__init__(self, name)
        self.durable = True
        self.auto_delete = False
        self.exclusive = False
        self.expiration = 0

    def __eq__(self, other):
        return isinstance(other, BaseQueue) and \
            self.name == other.name

    def __ne__(self, other):
        return not (self == other)


class Queue(BaseQueue):
    """
    An AMQP message queue.
    """

    def __init__(self, name=None, url=None):
        """
        :param name: The queue name.
        :type name: str
        :param url: The (optional) broker URL.
        :type url: str
        """
        BaseQueue.__init__(self, name or str(uuid4()))
        self.url = url

    @model
    def declare(self, url=None):
        """
        Declare the queue.
        :param url: The broker URL.
        :type url: str
        :raise: ModelError
        """
        url = url or self.url
        adapter = Adapter.find(url)
        impl = adapter.Queue(self.name)
        impl.durable = self.durable
        impl.auto_delete = self.auto_delete
        impl.expiration = self.expiration
        impl.exclusive = self.exclusive
        impl.declare(url)

    @model
    def delete(self, url=None):
        """
        Delete the queue.
        :param url: The broker URL.
        :type url: str
        :raise: ModelError
        """
        url = url or self.url
        adapter = Adapter.find(url)
        impl = adapter.Queue(self.name)
        impl.delete(url)

    @model
    def purge(self, url=None):
        """
        Purge (drain) all queued messages.
        :param url: The broker URL.
        :type url: str
        """
        url = url or self.url
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


# --- messenger --------------------------------------------------------------


class Messenger(Model):
    """
    Provides AMQP messaging.
    """

    def __init__(self, url):
        """
        :param url: The broker url.
        :type url: str
        """
        self.url = url

    def is_open(self):
        """
        Get whether the messenger has been opened.
        :return: True if open.
        :rtype bool
        """
        raise NotImplementedError()

    def open(self):
        """
        Open and configure the messenger.
        :raise: NotFound
        """
        raise NotImplementedError()

    def close(self):
        """
        Close the messenger.
        """
        raise NotImplementedError()

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *unused):
        self.close()


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
        raise NotImplementedError()

    def reject(self, message, requeue=True):
        """
        Reject the specified message.
        :param message: The message to reject.
        :param requeue: Requeue the message or discard it.
        :type requeue: bool
        """
        raise NotImplementedError()


class Reader(BaseReader):
    """
    An AMQP queue reader.
    :ivar authenticator: A message authenticator.
    :type authenticator: gofer.messaging.auth.Authenticator
    """

    def __init__(self, queue, url=None):
        """
        :param queue: The queue to read.
        :type queue: gofer.messaging.adapter.model.BaseQueue
        :param url: The broker url.
        :type url: str
        :see: gofer.messaging.adapter.url.URL
        """
        BaseReader.__init__(self, queue, url)
        adapter = Adapter.find(url)
        self._impl = adapter.Reader(queue, url)
        self.authenticator = None

    @model
    def is_open(self):
        """
        Get whether the reader has been opened.
        :return: True if open.
        :rtype bool
        """
        return self._impl.is_open()

    @model
    def open(self):
        """
        Open the reader.
        :raise: NotFound
        """
        self._impl.open()

    @model
    def close(self):
        """
        Close the reader.
        :raise: ModelError
        """
        self._impl.close()

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


# --- sender/producer --------------------------------------------------------


class BaseSender(Messenger):
    """
    :ivar durable: Messages sent are marked as durable.
    :type durable: bool
    """

    def __init__(self, url=None):
        """
        :param url: The broker url.
        :type url: str
        """
        Messenger.__init__(self, url)
        self.durable = True

    def send(self, address, content, ttl):
        """
        Send a message with content.
        :param address: An AMQP address.
        :type address: str
        :param content: The message content
        :param ttl: Time to Live (seconds)
        :type ttl: float
        :return: The message ID.
        :rtype: str
        """
        raise NotImplementedError()


class Sender(BaseSender):

    def __init__(self, url=None):
        """
        :param url: The broker url.
        :type url: str
        """
        BaseSender.__init__(self, url)
        adapter = Adapter.find(url)
        self._impl = adapter.Sender(url)

    @model
    def is_open(self):
        """
        Get whether the sender has been opened.
        :return: True if open.
        :rtype bool
        """
        return self._impl.is_open()

    @model
    def open(self):
        """
        Open the sender.
        :raise: ModelError
        """
        self._impl.open()

    @model
    def close(self):
        """
        Close the sender.
        :raise: ModelError
        """
        self._impl.close()

    @model
    def send(self, address, content, ttl=None):
        """
        Send a message with content.
        :param address: An AMQP address.
        :type address: str
        :param content: The message content
        :param ttl: Time to Live (seconds)
        :type ttl: float
        """
        self._impl.durable = self.durable
        self._impl.send(address, content, ttl)


class Producer(Messenger):
    """
    An AMQP message producer.
    :ivar authenticator: A message authenticator.
    :type authenticator: gofer.messaging.auth.Authenticator
    """

    def __init__(self, url=None):
        """
        :param url: The broker url.
        :type url: str
        """
        Messenger.__init__(self, url)
        adapter = Adapter.find(url)
        self._impl = adapter.Sender(url)
        self.authenticator = None

    @model
    def is_open(self):
        """
        Get whether the producer has been opened.
        :return: True if open.
        :rtype bool
        """
        return self._impl.is_open()

    @model
    def open(self):
        """
        Open the producer.
        :raise: ModelError
        """
        self._impl.open()

    @model
    def close(self):
        """
        Close the producer.
        :raise: ModelError
        """
        self._impl.close()

    @model
    def send(self, address, ttl=None, **body):
        """
        Send a message.
        :param address: An AMQP address.
        :type address: str
        :param ttl: Time to Live (seconds)
        :type ttl: float
        :keyword body: document body.
        :return: The message serial number.
        :rtype: str
        :raise: ModelError
        """
        sn = str(uuid4())
        routing = (None, address)
        document = Document(sn=sn, version=VERSION, routing=routing)
        document += body
        unsigned = document.dump()
        signed = auth.sign(self.authenticator, unsigned)
        self._impl.send(address, signed, ttl)
        return sn


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

    def close(self):
        """
        Close the connection.
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
    def close(self):
        """
        Close the connection.
        :raise: ModelError
        """
        self._impl.close()


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

    def __nonzero__(self):
        return (self.ca_certificate or
                self.client_certificate or
                self.client_key) is not None

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

    @staticmethod
    def find(url):
        """
        Find a broker by URL.
        :param url: A broker URL.
        :type url: str
        :return: The broker.
        :rtype: Broker
        """
        domain_id = URL(url).canonical
        try:
            return Domain.broker.find(domain_id)
        except NotFound:
            return Broker(url)

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
        return self.url.canonical

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

    def add(self):
        """
        Add this broker to the domain.
        """
        Domain.broker.add(self)

    def use_ssl(self):
        """
        Get whether SSL should be used.
        :return: True if SSL should be used.
        :rtype: bool
        """
        return self.url.is_ssl()

    def __str__(self):
        s = list()
        s.append('URL: %s' % self.url)
        s.append('SSL: %s' % self.ssl)
        return '|'.join(s)


# --- domain -----------------------------------------------------------------


class Domain(object):
    """
    Model object domains.
    :cvar broker: Collection of brokers.
    :type broker: _Domain
    """
    broker = _Domain()

