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

from amqplib.client_0_8 import Message

from gofer.messaging import auth
from gofer.messaging.model import getuuid, VERSION, Envelope
from gofer.transport.amqplib.endpoint import Endpoint, reliable


log = getLogger(__name__)


# --- utils ------------------------------------------------------------------


def message(body, ttl):
    if ttl:
        ms = ttl * 1000  # milliseconds
        return Message(body, expiration=str(ms))
    else:
        return Message(body)

@reliable
def send(endpoint, destination, ttl=None, **body):
    """
    Send a message.
    :param endpoint: An AMQP endpoint.
    :type endpoint: Endpoint
    :param destination: An AMQP destination.
    :type destination: gofer.transport.model.Destination
    :param ttl: Time to Live (seconds)
    :type ttl: float
    :keyword body: envelope body.
    :return: The message serial number.
    :rtype: str
    """
    sn = getuuid()
    routing_key = destination.routing_key
    routing = (endpoint.id(), routing_key)
    envelope = Envelope(sn=sn, version=VERSION, routing=routing)
    envelope += body
    unsigned = envelope.dump()
    signed = auth.sign(endpoint.authenticator, unsigned)
    channel = endpoint.channel()
    m = message(signed, ttl)
    channel.basic_publish(m, exchange=destination.exchange, routing_key=routing_key)
    log.debug('{%s} sent (%s)\n%s', endpoint.id(), routing_key, envelope)
    return sn


# --- producers --------------------------------------------------------------


class Producer(Endpoint):
    """
    An AMQP (message producer.
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
        return send(self, destination, ttl, **body)

    def broadcast(self, destinations, ttl=None, **body):
        """
        Broadcast a message to (N) queues.
        :param destinations: A list of AMQP destinations.
        :type destinations: [gofer.transport.node.Destination,..]
        :param ttl: Time to Live (seconds)
        :type ttl: float
        :keyword body: envelope body.
        :return: A list of (addr, sn).
        :rtype: list
        """
        sns = []
        for dst in destinations:
            sn = send(self, dst, ttl, **body)
            sns.append((repr(dst), sn))
        return sns


class BinaryProducer(Endpoint):

    @reliable
    def send(self, destination, content, ttl=None):
        routing_key = destination.routing_key
        channel = self.channel()
        m = message(content, ttl)
        channel.basic_publish(m, exchange=destination.exchange, routing_key=routing_key)
        log.debug('{%s} sent (binary)\n%s', self.id(), routing_key)

    @reliable
    def broadcast(self, destinations, content, ttl=None):
        for dst in destinations:
            self.send(dst, content, ttl)