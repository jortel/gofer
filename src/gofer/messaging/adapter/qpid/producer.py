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

from gofer.messaging.adapter.model import BaseSender
from gofer.messaging.adapter.qpid.reliability import reliable
from gofer.messaging.adapter.qpid.connection import Connection


log = getLogger(__name__)


class Sender(BaseSender):
    """
    An AMQP message sender.
    """

    def __init__(self, url):
        """
        :param url: The broker url.
        :type url: str
        """
        BaseSender.__init__(self, url)
        self.connection = Connection(url)
        self.session = None

    def is_open(self):
        """
        Get whether the sender has been opened.
        :return: True if open.
        :rtype bool
        """
        return self.session is not None

    @reliable
    def open(self):
        """
        Open the sender.
        """
        if self.is_open():
            # already opened
            return
        self.connection.open()
        self.session = self.connection.session()

    def repair(self):
        """
        Repair the sender.
        """
        self.session = None
        self.connection.close()
        self.connection.open()
        self.session = self.connection.session()

    def close(self):
        """
        Close the reader.
        """
        session = self.session
        self.session = None
        try:
            if session.connection.opened():
                session.close()
        except Exception:
            pass

    @reliable
    def send(self, address, content, ttl=None):
        """
        Send a message.
        :param address: An AMQP address.
        :type address: str
        :param content: The message content
        :type content: buf
        :param ttl: Time to Live (seconds)
        :type ttl: float
        """
        sender = self.session.sender(address)
        try:
            message = Message(content=content, durable=self.durable, ttl=ttl)
            sender.send(message)
            log.debug('sent (%s)', address)
        finally:
            sender.close()
