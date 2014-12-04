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
AMQP endpoint base classes.
"""
from logging import getLogger

from qpid.messaging import Disposition, RELEASED, REJECTED

from gofer.messaging.adapter.model import BaseEndpoint
from gofer.messaging.adapter.qpid.connection import Connection


log = getLogger(__name__)


class Endpoint(BaseEndpoint):
    """
    Base class for an AMQP endpoint.
    :ivar _connection: An AMQP session.
    :type _connection: qpid.messaging.Channel
    :ivar _channel: An AMQP session.
    :type _channel: qpid.messaging.Session
    """

    def __init__(self, url):
        """
        :param url: The broker url <adapter>://<user>/<pass>@<host>:<port>.
        :type url: str
        """
        BaseEndpoint.__init__(self, url)
        self._connection = None
        self._channel = None

    def is_open(self):
        """
        Get whether the endpoint has been opened.
        :return: True if open.
        :rtype bool
        """
        return self._channel or self._connection

    def open(self):
        """
        Open and configure the endpoint.
        """
        if self.is_open():
            # already open
            return
        self._connection = Connection(self.url)
        self._connection.open()
        self._channel = self._connection.channel()

    def channel(self):
        """
        Get a session for the open connection.
        :return: An open session.
        :rtype: qpid.messaging.Session
        """
        return self._channel

    def ack(self, message):
        """
        Acknowledge all messages received on the session.
        :param message: The message to acknowledge.
        :type message: qpid.messaging.Message
        """
        self._channel.acknowledge(message=message)

    def reject(self, message, requeue=True):
        """
        Reject the specified message.
        :param message: The message to reject.
        :type message: qpid.messaging.Message
        :param requeue: Requeue the message or discard it.
        :type requeue: bool
        """
        if requeue:
            disposition = Disposition(RELEASED)
        else:
            disposition = Disposition(REJECTED)
        self._channel.acknowledge(message=message, disposition=disposition)

    def close(self, hard=False):
        """
        Close the endpoint.
        :param hard: Force the connection closed.
        :type hard: bool
        """
        if not self.is_open():
            # not open
            return
        self._close_channel()
        self._connection.close(hard)
        self._connection = None
        self._channel = None

    def _close_channel(self):
        """
        Safely close the channel.
        """
        try:
            self._channel.close()
        except Exception, e:
            log.debug(str(e))

    def __str__(self):
        return 'Endpoint id:%s broker @ %s' % (self.id(), self.url)
