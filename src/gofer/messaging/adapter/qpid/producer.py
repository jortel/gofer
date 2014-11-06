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

"""
Contains AMQP message producer classes.
"""

from logging import getLogger
from uuid import uuid4

from qpid.messaging import Message

from gofer.messaging import auth
from gofer.messaging.model import VERSION, Document
from gofer.messaging.provider.model import BaseProducer, BasePlainProducer
from gofer.messaging.provider.qpid.endpoint import Endpoint


log = getLogger(__name__)


# --- utils ------------------------------------------------------------------


def send(endpoint, destination, ttl=None, **body):
    """
    Send a message.
    :param endpoint: An AMQP endpoint.
    :type endpoint: gofer.messaging.provider.model.BaseEndpoint
    :param destination: An AMQP destination.
    :type destination: gofer.messaging.provider.model.Destination
    :param ttl: Time to Live (seconds)
    :type ttl: float
    :keyword body: document body.
    :return: The message serial number.
    :rtype: str
    """
    sn = str(uuid4())
    if destination.exchange:
        address = '/'.join((destination.exchange, destination.routing_key))
    else:
        address = destination.routing_key
    routing = (endpoint.id(), destination.routing_key)
    document = Document(sn=sn, version=VERSION, routing=routing)
    document += body
    unsigned = document.dump()
    signed = auth.sign(endpoint.authenticator, unsigned)
    message = Message(content=signed, durable=True, ttl=ttl)
    sender = endpoint.channel().sender(address)
    sender.send(message)
    sender.close()
    log.debug('sent (%s) %s', destination, document)
    return sn


# --- producers --------------------------------------------------------------


class Producer(BaseProducer):
    """
    An AMQP (message producer.
    """

    def __init__(self, url=None):
        """
        :param url: The broker url.
        :type url: str
        """
        BaseProducer.__init__(self, url)
        self._endpoint = Endpoint(url)

    def endpoint(self):
        """
        Get a concrete object.
        :return: A concrete object.
        :rtype: BaseEndpoint
        """
        return self._endpoint

    def send(self, destination, ttl=None, **body):
        """
        Send a message.
        :param destination: An AMQP destination.
        :type destination: gofer.messaging.provider.model.Destination
        :param ttl: Time to Live (seconds)
        :type ttl: float
        :keyword body: document body.
        :return: The message serial number.
        :rtype: str
        """
        return send(self, destination, ttl, **body)

    def broadcast(self, destinations, ttl=None, **body):
        """
        Broadcast a message to (N) queues.
        :param destinations: A list of AMQP destinations.
        :type destinations: [gofer.messaging.provider.node.Node,..]
        :param ttl: Time to Live (seconds)
        :type ttl: float
        :keyword body: document body.
        :return: A list of (addr,sn).
        :rtype: list
        """
        sns = []
        for dst in destinations:
            sn = send(self, dst, ttl, **body)
            sns.append((repr(dst), sn))
        return sns


class PlainProducer(BasePlainProducer):
    """
    An Plain AMQP message producer.
    """

    def __init__(self, url=None):
        """
        :param url: The broker url.
        :type url: str
        """
        BasePlainProducer.__init__(self, url)
        self._endpoint = Endpoint(url)

    def endpoint(self):
        """
        Get a concrete object.
        :return: A concrete object.
        :rtype: BaseEndpoint
        """
        return self._endpoint

    def send(self, destination, content, ttl=None):
        """
        Send a message.
        :param destination: An AMQP destination.
        :type destination: gofer.messaging.provider.model.Destination
        :param content: The message content
        :type content: buf
        :param ttl: Time to Live (seconds)
        :type ttl: float
        """
        if destination.exchange:
            address = '/'.join((destination.exchange, destination.routing_key))
        else:
            address = destination.routing_key
        message = Message(content=content, durable=True, ttl=ttl)
        sender = self.channel().sender(address)
        sender.send(message)
        sender.close()
        log.debug('sent (%s) <Plain>', destination)

    def broadcast(self, destinations, content, ttl=None):
        """
        Broadcast a message to (N) queues.
        :param destinations: A list of AMQP destinations.
        :type destinations: [gofer.messaging.provider.node.Node,..]
        :param content: The message content
        :type content: buf
        """
        for dst in destinations:
            self.send(dst, content, ttl)
