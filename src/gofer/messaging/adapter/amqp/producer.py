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

from logging import getLogger
from uuid import uuid4

from amqp import Message

from gofer.messaging import auth
from gofer.messaging.model import VERSION, Document
from gofer.messaging.adapter.model import BaseProducer, BasePlainProducer
from gofer.messaging.adapter.amqp.endpoint import Endpoint, reliable


log = getLogger(__name__)


# --- utils ------------------------------------------------------------------


def build_message(body, ttl):
    """
    Construct a message object.
    :param body: The message body.
    :param ttl: Time to Live (seconds)
    :type ttl: float
    :return: The message.
    :rtype: Message
    """
    if ttl:
        ms = ttl * 1000  # milliseconds
        return Message(body, durable=True, expiration=str(ms))
    else:
        return Message(body, durable=True)

@reliable
def send(endpoint, destination, ttl=None, **body):
    """
    Send a message.
    :param endpoint: An AMQP endpoint.
    :type endpoint: gofer.messaging.adapter.model.BaseEndpoint
    :param destination: An AMQP destination.
    :type destination: gofer.messaging.adapter.model.Destination
    :param ttl: Time to Live (seconds)
    :type ttl: float
    :keyword body: document body.
    :return: The message serial number.
    :rtype: str
    """
    sn = str(uuid4())
    routing_key = destination.routing_key
    routing = (endpoint.id(), routing_key)
    document = Document(sn=sn, version=VERSION, routing=routing)
    document += body
    unsigned = document.dump()
    signed = auth.sign(endpoint.authenticator, unsigned)
    channel = endpoint.channel()
    m = build_message(signed, ttl)
    channel.basic_publish(m, exchange=destination.exchange, routing_key=routing_key)
    log.debug('sent (%s) %s', destination, document)
    return sn


def plain_send(self, destination, content, ttl=None):
    """
    Send a message with *raw* content.
    :param destination: An AMQP destination.
    :type destination: gofer.messaging.adapter.model.Destination
    :param content: The message content
    :param ttl: Time to Live (seconds)
    :type ttl: float
    :return: The message ID.
    :rtype: str
    """
    routing_key = destination.routing_key
    channel = self.channel()
    m = build_message(content, ttl)
    channel.basic_publish(m, exchange=destination.exchange, routing_key=routing_key)
    log.debug('sent (%s) <Plain>', destination)
    return m.id


# --- producers --------------------------------------------------------------


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
        :type destination: gofer.messaging.adapter.model.Destination
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
        :type destinations: [gofer.messaging.adapter.node.Destination,..]
        :param ttl: Time to Live (seconds)
        :type ttl: float
        :keyword body: document body.
        :return: A list of (addr, sn).
        :rtype: list
        """
        sns = []
        for dst in destinations:
            sn = send(self, dst, ttl, **body)
            sns.append((repr(dst), sn))
        return sns


class PlainProducer(BasePlainProducer):

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

    @reliable
    def send(self, destination, content, ttl=None):
        return plain_send(self, destination, content, ttl=ttl)

    @reliable
    def broadcast(self, destinations, content, ttl=None):
        id_list = []
        for destination in destinations:
            sn = plain_send(self, destination, content, ttl=ttl)
            id_list.append((repr(destination), sn))
        return id_list