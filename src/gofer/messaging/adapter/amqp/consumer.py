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

import select

from Queue import Empty
from Queue import Queue as Inbox
from logging import getLogger

from gofer.messaging.adapter.model import BaseReader, Message
from gofer.messaging.adapter.amqp.connection import Connection
from gofer.messaging.adapter.amqp.reliability import reliable


log = getLogger(__name__)


NO_DELAY = 0
DELIVERY_TAG = 'delivery_tag'


class Reader(BaseReader):
    """
    An AMQP message reader.
    """

    def __init__(self, node, url):
        """
        :param node: The AMQP node to read.
        :type node: gofer.messaging.adapter.model.Node
        :param url: The broker url.
        :type url: str
        :see: gofer.messaging.adapter.url.URL
        """
        BaseReader.__init__(self, node, url)
        self.connection = Connection(url)
        self.channel = None
        self.receiver = None

    def is_open(self):
        """
        Get whether the messenger has been opened.
        :return: True if open.
        :rtype bool
        """
        return self.receiver is not None

    @reliable
    def open(self):
        """
        Open the reader.
        :raise: NotFound
        """
        if self.is_open():
            # already opened
            return
        self.connection.open()
        self.channel = self.connection.channel()
        receiver = Receiver(self)
        self.receiver = receiver.open()

    def close(self):
        """
        Close the reader.
        """
        receiver = self.receiver
        self.receiver = None

        try:
            receiver.close()
        except Exception:
            pass

        channel = self.channel
        self.channel = None

        try:
            channel.close()
        except Exception:
            pass


    @reliable
    def get(self, timeout=None):
        """
        Get the next message from the queue.
        :param timeout: The read timeout in seconds.
        :type timeout: int
        :return: The next message or None.
        :rtype: Message
        """
        try:
            impl = self.receiver.fetch(timeout or NO_DELAY)
            return Message(self, impl, impl.body)
        except Empty:
            pass

    @reliable
    def ack(self, message):
        """
        Ack the specified message.
        :param message: The message to acknowledge.
        :type message: amqp.Message
        """
        self.channel.basic_ack(message.delivery_info[DELIVERY_TAG])

    @reliable
    def reject(self, message, requeue=True):
        """
        Reject the specified message.
        :param message: The message to reject.
        :type message: amqp.Message
        :param requeue: Requeue the message or discard it.
        :type requeue: bool
        """
        self.channel.basic_reject(message.delivery_info[DELIVERY_TAG], requeue)


class Receiver(object):
    """
    Message receiver.
    :ivar reader: A message reader.
    :type reader: Reader
    :ivar inbox: The message inbox.
    :type inbox: Inbox
    """

    @staticmethod
    def _wait(fd, channel, timeout):
        """
        Wait on channel.
        :param fd: The connection file descriptor.
        :type fd: int
        :return: The channel.
        :rtype: amqp.channel.Channel
        :param timeout: The read timeout in seconds.
        :type timeout: int
        """
        if len(channel.method_queue):
            channel.wait()
            return
        epoll = select.epoll()
        epoll.register(fd, select.EPOLLIN)
        try:
            if epoll.poll(timeout):
                channel.wait()
        finally:
            epoll.unregister(fd)
            epoll.close()

    def __init__(self, reader):
        """
        :param reader: A message reader.
        :type reader: Reader
        """
        self.reader = reader
        self.inbox = Inbox()
        self.tag = None

    def channel(self):
        """
        :return: The channel.
        :rtype: amqp.channel.Channel
        """
        return self.reader.channel

    def open(self):
        """
        Open the receiver.
        :return: self
        :rtype: Receiver
        """
        fn = self.inbox.put
        channel = self.channel()
        address = self.reader.node.address
        self.tag = channel.basic_consume(address, callback=fn)
        return self

    def close(self):
        """
        Close the receiver.
        """
        try:
            channel = self.channel()
            channel.basic_cancel(self.tag)
        except Exception, e:
            log.debug(str(e))

    def fetch(self, timeout=None):
        """
        Fetch the next message
        :param timeout: The read timeout in seconds.
        :type timeout: int
        :return: The next message.
        :rtype: amqp.message.Message
        :raise: Empty
        """
        inbox = self.inbox
        if inbox.empty():
            channel = self.channel()
            fd = channel.connection.sock.fileno()
            self._wait(fd, channel, timeout)
        return inbox.get(block=False)
