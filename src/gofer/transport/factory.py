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

import os

from logging import getLogger

from gofer.transport.broker import URL


log = getLogger(__name__)


# --- constants --------------------------------------------------------------

# the default URL
DEFAULT_URL = 'tcp://localhost:5672'


# symbols required to be provided by all transports
REQUIRED = [
    'Exchange',
    'Broker',
    'Endpoint',
    'Queue',
    'Producer',
    'BinaryProducer',
    'Reader',
]


# --- exceptions -------------------------------------------------------------


class TransportError(Exception):
    pass


class NoTransportsLoaded(TransportError):

    DESCRIPTION = 'No transports loaded'

    def __str__(self):
        return self.DESCRIPTION


class TransportNotFound(TransportError):

    DESCRIPTION = 'Transport: %s, not-found'

    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.DESCRIPTION % self.name


# --- factory ----------------------------------------------------------------


class Transport:
    """
    The transport API.
    :cvar bindings: Transport packages mapped by URL.
    :cvar bindings: dict
    """

    plugins = {}
    bindings = {}

    @classmethod
    def load_plugins(cls):
        _dir = os.path.dirname(__file__)
        for name in os.listdir(_dir):
            path = os.path.join(_dir, name)
            if not os.path.isdir(path):
                continue
            try:
                package = '.'.join((__package__, name))
                pkg = __import__(package, {}, {}, REQUIRED)
                cls.plugins[name] = pkg
                cls.plugins[package] = pkg
            except ImportError:
                log.debug(name)

    @classmethod
    def bind(cls, url=None, package=None):
        """
        Bind a URL to the specified package.
        :param url: The agent/broker URL.
        :type url: str, URL
        :param package: The python package providing the transport.
        :type package: str
        :return: The bound python module.
        """
        if not cls.plugins:
            raise NoTransportsLoaded()
        if not url:
            url = DEFAULT_URL
        if not isinstance(url, URL):
            url = URL(url)
        if not package:
            package = sorted(cls.plugins)[0]
        try:
            plugin = cls.plugins[package]
            cls.bindings[url] = plugin
            log.info('transport: %s bound to url: %s', plugin, url)
            return plugin
        except KeyError:
            raise TransportNotFound(package)

    def __init__(self, url=None, package=None):
        """
        :param url: The agent/broker URL.
        :type url: str, URL
        :param package: The python package providing the transport.
        :type package: str
        """
        if not url:
            url = DEFAULT_URL
        if not isinstance(url, URL):
            url = URL(url)
        self.url = url
        try:
            self.package = self.bindings[url]
        except KeyError:
            self.package = self.bind(url, package)

    def broker(self):
        """
        Get an AMQP broker.
        :return: The broker provided by the transport.
        :rtype: gofer.transport.broker.Broker
        """
        return self.Broker(self.url)

    def exchange(self, name, policy=None):
        """
        Get and AMQP exchange object.
        :param name: The exchange name.
        :type name: str
        :param policy: The routing policy.
        :type policy: str
        :return: The exchange object provided by the transport.
        :rtype: gofer.transport.model.Exchange
        """
        return self.Exchange(name, policy=policy)

    def queue(self, name, exchange=None, routing_key=None):
        """
        Get an AMQP topic queue.
        :param name: The topic name.
        :param name: str
        :param exchange: An AMQP exchange.
        :param exchange: str
        :param routing_key: An AMQP routing key.
        :type routing_key: str
        :return: The queue object provided by the transport.
        :rtype: gofer.transport.node.Queue.
        """
        return self.Queue(name, exchange=exchange, routing_key=routing_key)

    def producer(self, uuid=None):
        """
        Get an AMQP message producer.
        :param uuid: The (optional) producer ID.
        :type uuid: str
        :return: The broker provided by the transport.
        :rtype: gofer.transport.endpoint.Endpoint.
        """
        return self.Producer(uuid, url=self.url)

    def binary_producer(self, uuid=None):
        """
        Get an AMQP binary message producer.
        :param uuid: The (optional) producer ID.
        :type uuid: str
        :return: The producer provided by the transport.
        :rtype: gofer.transport.endpoint.Endpoint.
        """
        return self.BinaryProducer(uuid, url=self.url)

    def reader(self, queue, uuid=None):
        """
        Get an AMQP message reader.
        :param queue: The AMQP node.
        :type queue: gofer.transport.model.Queue
        :param uuid: The (optional) producer ID.
        :type uuid: str
        :return: The reader provided by the transport.
        :rtype: gofer.transport.endpoint.Endpoint.
        """
        return self.Reader(queue, uuid=uuid, url=self.url)

    def __getattr__(self, name):
        return getattr(self.package, name)
