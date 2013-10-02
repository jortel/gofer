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

from gofer.messaging import *
from gofer.messaging.endpoint import Endpoint
from qpid.messaging import Message
from logging import getLogger

log = getLogger(__name__)


class Producer(Endpoint):
    """
    An AMQP (abstract) message producer.
    """

    def send(self, destination, ttl=None, **body):
        """
        Send a message.
        :param destination: An AMQP destination.
        :type destination: Destination
        :param ttl: Time to Live (seconds)
        :type ttl: float
        :keyword body: envelope body.
        :return: The message serial number.
        :rtype: str
        """
        sn = getuuid()
        address = str(destination)
        routing = (self.id(), address.split(';')[0])
        envelope = Envelope(sn=sn, version=version, routing=routing)
        envelope += body
        json = envelope.dump()
        message = Message(content=json, durable=True, ttl=ttl)
        sender = self.session().sender(address)
        sender.send(message)
        sender.close()
        log.debug('{%s} sent (%s)\n%s', self.id(), address, envelope)
        return sn

    def broadcast(self, destinations, **body):
        """
        Broadcast a message to (N) queues.
        :param destinations: A list of AMQP destinations.
        :type destinations: [Destination,..]
        :keyword body: envelope body.
        :return: A list of (addr,sn).
        :rtype: list
        """
        sns = []
        for dst in destinations:
            sn = self.send(str(dst), **body)
            sns.append((repr(dst),sn))
        return sns


class BinaryProducer(Endpoint):
    """
    An binary AMQP message producer.
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
        """
        address = str(destination)
        message = Message(content=content, durable=True, ttl=ttl)
        sender = self.session().sender(address)
        sender.send(message)
        sender.close()
        log.debug('{%s} sent (%s)\n%s', self.id(), address)

    def broadcast(self, destinations, content, ttl=None):
        """
        Broadcast a message to (N) queues.
        :param destinations: A list of AMQP destinations.
        :type destinations: [Destination,..]
        :param content: The message content
        :type content: buf
        """
        for dst in destinations:
            sn = self.send(str(dst), content, ttl)
