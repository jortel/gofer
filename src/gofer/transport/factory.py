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
import logging


log = logging.getLogger(__name__)


# --- constants --------------------------------------------------------------

# __package__ not supported in python 2.4
PACKAGE = '.'.join(__name__.split('.')[:-1])

# symbols required to be provided by all transports
REQUIRED = [
    'PROVIDES',
    'Exchange',
    'Broker',
    'Endpoint',
    'Queue',
    'Producer',
    'BinaryProducer',
    'Reader',
    'send',
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
    :cvar plugins: Loaded transport plugins.
    :cvar plugins: dict
    """

    plugins = {}

    @classmethod
    def load_plugins(cls):
        _dir = os.path.dirname(__file__)
        for name in os.listdir(_dir):
            path = os.path.join(_dir, name)
            if not os.path.isdir(path):
                continue
            try:
                package = '.'.join((PACKAGE, name))
                pkg = __import__(package, {}, {}, REQUIRED)
                cls.plugins[name] = pkg
                cls.plugins[package] = pkg
                for capability in pkg.PROVIDES:
                    cls.plugins[capability] = pkg
            except (ImportError, AttributeError):
                log.exception(path)

    def __init__(self, package=None):
        """
        :param package: The python package providing the transport.
        :type package: str
        """
        loaded = sorted(self.plugins)
        if not loaded:
            raise NoTransportsLoaded()
        if not package:
            self.package = loaded[0]
            self.plugin = self.plugins[loaded[0]]
            return
        try:
            self.package = package
            self.plugin = self.plugins[package]
        except KeyError:
            raise TransportNotFound(package)

    @property
    def name(self):
        """
        The transport package name.
        :return: The transport package name.
        :rtype: str
        """
        return self.plugin.__name__

    def broker(self, url):
        """
        Get an AMQP broker.
        :param url: The url for the broker.
        :type url: str
        :return: The broker provided by the transport.
        :rtype: gofer.transport.broker.Broker
        """
        return self.plugin.Broker(url)

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
        return self.plugin.Exchange(name, policy=policy)

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
        :rtype: gofer.transport.model.Queue.
        """
        return self.plugin.Queue(name, exchange=exchange, routing_key=routing_key)

    def producer(self, url, uuid=None):
        """
        Get an AMQP message producer.
        :param url: The url for the broker.
        :type url: str
        :param uuid: The (optional) producer ID.
        :type uuid: str
        :return: The broker provided by the transport.
        :rtype: gofer.transport.model.Producer.
        """
        return self.plugin.Producer(uuid, url=url)

    def binary_producer(self, url, uuid=None):
        """
        Get an AMQP binary message producer.
        :param url: The url for the broker.
        :type url: str
        :param uuid: The (optional) producer ID.
        :type uuid: str
        :return: The producer provided by the transport.
        :rtype: gofer.transport.model.BinaryProducer.
        """
        return self.plugin.BinaryProducer(uuid, url=url)

    def reader(self, url, queue, uuid=None):
        """
        Get an AMQP message reader.
        :param url: The url for the broker.
        :type url: str
        :param queue: The AMQP node.
        :type queue: gofer.transport.model.Queue
        :param uuid: The (optional) producer ID.
        :type uuid: str
        :return: The reader provided by the transport.
        :rtype: gofer.transport.model.Reader.
        """
        return self.plugin.Reader(queue, uuid=uuid, url=url)
