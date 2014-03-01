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

from qpid.messaging import Message

from gofer.messaging import auth
from gofer.messaging.model import getuuid, VERSION, Envelope
from gofer.transport.qpid.endpoint import Endpoint


log = getLogger(__name__)


# --- utils ------------------------------------------------------------------


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
    if destination.exchange:
        address = '/'.join((destination.exchange, destination.routing_key))
    else:
        address = destination.routing_key
    routing = (endpoint.id(), destination.routing_key)
    envelope = Envelope(sn=sn, version=VERSION, routing=routing)
    envelope += body
    unsigned = envelope.dump()
    signed = auth.sign(endpoint.authenticator, unsigned)
    message = Message(content=signed, durable=True, ttl=ttl)
    sender = endpoint.session().sender(address)
    sender.send(message)
    sender.close()
    log.debug('{%s} sent (%s)\n%s', endpoint.id(), address, envelope)
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
        :type destinations: [gofer.transport.node.Node,..]
        :param ttl: Time to Live (seconds)
        :type ttl: float
        :keyword body: envelope body.
        :return: A list of (addr,sn).
        :rtype: list
        """
        sns = []
        for dst in destinations:
            sn = send(self, dst, ttl, **body)
            sns.append((repr(dst), sn))
        return sns


class BinaryProducer(Endpoint):
    """
    An binary AMQP message producer.
    """

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
        if destination.exchange:
            address = '/'.join((destination.exchange, destination.routing_key))
        else:
            address = destination.routing_key
        message = Message(content=content, durable=True, ttl=ttl)
        sender = self.session().sender(address)
        sender.send(message)
        sender.close()
        log.debug('{%s} sent (%s)\n%s', self.id(), address)

    def broadcast(self, destinations, content, ttl=None):
        """
        Broadcast a message to (N) queues.
        :param destinations: A list of AMQP destinations.
        :type destinations: [gofer.transport.node.Node,..]
        :param content: The message content
        :type content: buf
        """
        for dst in destinations:
            self.send(dst, content, ttl)
