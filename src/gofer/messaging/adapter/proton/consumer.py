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
Provides AMQP message consumer classes.
"""

from logging import getLogger

from proton import Timeout

from gofer.messaging.adapter.model import BaseReader, Message
from gofer.messaging.adapter.proton.connection import Connection
from gofer.messaging.adapter.proton.reliability import reliable


log = getLogger(__name__)


NO_DELAY = 0.010


class Reader(BaseReader):
    """
    An AMQP message reader.
    :ivar connection: A proton connection
    :type connection: Connection
    :ivar receiver: An AMQP receiver to read.
    :type receiver: proton.utils.BlockingReceiver
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
        """
        if self.is_open():
            # already open
            return
        self.connection.open()
        self.receiver = self.connection.receiver(self.node.address)

    def close(self):
        """
        Close the reader.
        :raise: NotFound
        """
        receiver = self.receiver
        self.receiver = None

        try:
            receiver.close()
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
            impl = self.receiver.receive(timeout or NO_DELAY)
            return Message(self, impl, impl.body)
        except Timeout:
            pass

    @reliable
    def ack(self, message):
        """
        Acknowledge all messages received on the session.
        :param message: The message to acknowledge.
        :type message: proton.Message
        """
        self.receiver.accept()

    @reliable
    def reject(self, message, requeue=True):
        """
        Reject the specified message.
        :param message: The message to reject.
        :type message: proton.Message
        :param requeue: Requeue the message or discard it.
        :type requeue: bool
        """
        if requeue:
            self.receiver.release()
        else:
            self.receiver.reject()
