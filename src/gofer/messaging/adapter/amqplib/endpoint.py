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

from time import sleep
from logging import getLogger

from amqplib.client_0_8 import AMQPChannelException

from gofer.messaging.adapter.model import BaseEndpoint
from gofer.messaging.adapter.amqplib.connection import Connection, CONNECTION_EXCEPTIONS


log = getLogger(__name__)


# --- constants --------------------------------------------------------------


DELIVERY_TAG = 'delivery_tag'


# --- reconnect decorator ----------------------------------------------------


def reliable(fn):
    def _fn(endpoint, *args, **kwargs):
        while True:
            try:
                return fn(endpoint, *args, **kwargs)
            except CONNECTION_EXCEPTIONS:
                endpoint.close(hard=True)
                sleep(3)
                endpoint.open()
    return _fn


# --- endpoint wrapper decorator ---------------------------------------------


def endpoint(fn):
    def _fn(url):
        _endpoint = Endpoint(url)
        _endpoint.open()
        try:
            return fn(_endpoint)
        finally:
            _endpoint.close()
    return _fn


# --- endpoint ---------------------------------------------------------------


class Endpoint(BaseEndpoint):
    """
    Base class for an AMQP endpoint.
    :ivar _connection: A connection.
    :type _connection: Connection
    :ivar _channel: An AMQP channel.
    :type _channel: amqplib.client_0_8.Channel
    """

    def __init__(self, url):
        """
        :param url: The broker url.
        :type url: str
        """
        BaseEndpoint.__init__(self, url)
        self._connection = None
        self._channel = None

    def channel(self):
        """
        Get a channel for the open connection.
        :return: An open channel.
        :rtype: amqplib.client_0_8.Channel
        """
        return self._channel

    def is_open(self):
        """
        Get whether the endpoint has been opened.
        :return: True if open.
        :rtype bool
        """
        return self._channel and self._connection

    def open(self):
        """
        Open and configure the endpoint.
        """
        if self.is_open():
            # already open
            return
        connection = Connection(self.url)
        connection.open()
        self._connection = connection
        self._channel = connection.channel()

    @reliable
    def ack(self, message):
        """
        Ack the specified message.
        :param message: The message to acknowledge.
        :type message: amqplib.client_0_8.Message
        """
        self._channel.basic_ack(message.delivery_info[DELIVERY_TAG])

    @reliable
    def reject(self, message, requeue=True):
        """
        Reject the specified message.
        :param message: The message to reject.
        :type message: amqplib.client_0_8.Message
        :param requeue: Requeue the message or discard it.
        :type requeue: bool
        """
        self._channel.basic_reject(message.delivery_info[DELIVERY_TAG], requeue)

    def close(self, hard=False):
        """
        Close the endpoint.
        :param hard: Force the connection closed.
        :type hard: bool
        """
        try:
            if not self.is_open():
                # not open
                return
            self._channel.close()
            self._connection.close(hard)
            self._channel = None
            self._connection = None
        except (CONNECTION_EXCEPTIONS, AMQPChannelException), e:
            log.exception(str(e))
