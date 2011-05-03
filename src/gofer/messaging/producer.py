#
# Copyright (c) 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
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
        @param destination: An AMQP destination.
        @type destination: L{Destination}
        @param ttl: Time to Live (seconds)
        @type ttl: float
        @keyword body: envelope body.
        @return: The message serial number.
        @rtype: str
        """
        sn = getuuid()
        envelope = Envelope(sn=sn, version=version, origin=self.id())
        envelope.update(body)
        json = envelope.dump()
        message = Message(content=json, durable=True, ttl=ttl)
        address = str(destination)
        sender = self.session().sender(address)
        sender.send(message)
        sender.close()
        log.debug('{%s} sent (%s)\n%s', self.id(), address, envelope)
        return sn

    def broadcast(self, destinations, **body):
        """
        Broadcast a message to (N) queues.
        @param destinations: A list of AMQP destinations.
        @type destinations: [L{Destination},..]
        @keyword body: envelope body.
        @return: A list of (addr,sn).
        @rtype: list
        """
        sns = []
        for dst in destinations:
            sn = Producer.send(self, str(dst), **body)
            sns.append((repr(dst),sn))
        return sns
