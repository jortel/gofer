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
from gofer.messaging.adapter.amqp.endpoint import Endpoint, reliable


log = getLogger(__name__)


NO_DELAY = 0


class Reader(BaseReader):
    """
    An AMQP message reader.
    :ivar queue: The AMQP queue to read.
    :type queue: gofer.messaging.adapter.model.Queue
    """

    def __init__(self, queue, url=None):
        """
        :param queue: The queue to consumer.
        :type queue: gofer.messaging.adapter.model.BaseQueue
        :param url: The broker url.
        :type url: str
        :see: gofer.messaging.adapter.url.URL
        """
        BaseReader.__init__(self, queue, url)
        self._endpoint = Endpoint(url)
        self._receiver = None

    def open(self):
        """
        Open the reader.
        """
        if self.is_open():
            # open
            return
        BaseReader.open(self)
        self._receiver = Receiver(self)
        self._receiver.open()

    def close(self, hard=False):
        """
        Close the reader.
        :param hard: Force the connection closed.
        :type hard: bool
        """
        if not self.is_open():
            # closed
            return
        self._receiver.close()
        BaseReader.close(self, hard)

    def endpoint(self):
        """
        Get a concrete object.
        :return: A concrete object.
        :rtype: BaseEndpoint
        """
        return self._endpoint

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
            impl = self._receiver.fetch(timeout or NO_DELAY)
            return Message(self, impl, impl.body)
        except Empty:
            pass


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
        return self.reader.channel()

    def open(self):
        """
        Open the receiver.
        """
        fn = self.inbox.put
        channel = self.channel()
        name = self.reader.queue.name
        self.tag = channel.basic_consume(name, callback=fn)

    def close(self):
        """
        Close the receiver.
        """
        try:
            channel = self.channel()
            channel.basic_cancel(self.tag)
            self.tag = None
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
