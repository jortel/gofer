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

from amqp import Message

from gofer.messaging.adapter.model import BaseSender
from gofer.messaging.adapter.amqp.connection import Connection
from gofer.messaging.adapter.amqp.reliability import reliable


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
    properties = {}

    if ttl:
        ms = ttl * 1000  # milliseconds
        properties.update(expiration=str(ms))

    if durable:
        properties.update(delivery_mode=2)
    else:
        properties.update(delivery_mode=1)

    return Message(body, **properties)


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
        self.channel = None

    def is_open(self):
        """
        Get whether the sender has been opened.
        :return: True if open.
        :rtype bool
        """
        return self.channel is not None

    def open(self):
        """
        Open the reader.
        """
        if self.is_open():
            # already opened
            return
        self.connection.open()
        self.channel = self.connection.channel()

    def close(self):
        """
        Close the reader.
        """
        channel = self.channel
        self.channel = None

        try:
            channel.close()
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
        parts = address.split('/')
        if len(parts) > 1:
            exchange = parts[0]
        else:
            exchange = ''
        key = parts[-1]
        message = build_message(content, ttl, self.durable)
        self.channel.basic_publish(message, mandatory=True, exchange=exchange, routing_key=key)
        log.debug('sent (%s)', address)
