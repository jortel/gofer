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

from proton import Message

from gofer.messaging.adapter.model import BaseSender
from gofer.messaging.adapter.proton.connection import Connection
from gofer.messaging.adapter.proton.reliability import reliable


log = getLogger(__name__)


def build_message(body, ttl, durable):
    """
    Construct a message object.
    :param body: The message body.
    :param ttl: Time to Live (seconds)
    :type ttl: float
    :param durable: The message is durable.
    :type durable: bool
    :return: The message.
    :rtype: Message
    """
    if ttl:
        return Message(body=body, durable=durable, ttl=ttl)
    else:
        return Message(body=body, durable=durable)


class Sender(BaseSender):
    """
    An AMQP message sender.
    :ivar connection: A proton connection.
    :type connection: Connection
    """

    def __init__(self, url):
        """
        :param url: The broker url.
        :type url: str
        """
        BaseSender.__init__(self, url)
        self.connection = Connection(url)

    def is_open(self):
        """
        Get whether the messenger has been opened.
        :return: True if open.
        :rtype bool
        """
        return self.connection.is_open()

    @reliable
    def open(self):
        """
        Open the sender.
        """
        if self.is_open():
            # already opened
            return
        self.connection.open()

    def repair(self):
        """
        Repair the sender.
        """
        self.close()
        self.connection.close()
        self.connection.open()

    def close(self):
        """
        Close the sender.
        """
        pass

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
        sender = self.connection.sender(address)
        try:
            message = build_message(content, ttl, self.durable)
            sender.send(message)
            log.debug('sent (%s)', address)
        finally:
            sender.close()
