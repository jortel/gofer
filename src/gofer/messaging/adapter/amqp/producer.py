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
from gofer.messaging.adapter.amqp.endpoint import Endpoint, reliable
from gofer.messaging.adapter.amqp.model import Route


log = getLogger(__name__)


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


class Sender(BaseSender):
    """
    An AMQP message sender.
    """

    def __init__(self, url=None):
        """
        :param url: The broker url.
        :type url: str
        """
        BaseSender.__init__(self, url)
        self._endpoint = Endpoint(url)
        self._link = None

    def endpoint(self):
        """
        Get a concrete object.
        :return: A concrete object.
        :rtype: BaseEndpoint
        """
        return self._link or self._endpoint

    def link(self, messenger):
        """
        Link to another messenger.
        :param messenger: A messenger to link with.
        :type messenger: gofer.messaging.adapter.model.Messenger
        """
        self._link = messenger.endpoint()

    def unlink(self):
        """
        Unlink with another messenger.
        """
        self._link = None

    @reliable
    def send(self, route, content, ttl=None):
        """
        Send a message.
        :param route: An AMQP route.
        :type route: str
        :param content: The message content
        :type content: buf
        :param ttl: Time to Live (seconds)
        :type ttl: float
        """
        channel = self.channel()
        message = build_message(content, ttl)
        route = Route(route)
        exchange = route.exchange.name
        key = route.queue.name
        channel.basic_publish(message, exchange=exchange, routing_key=key)
        log.debug('sent (%s)', route)
