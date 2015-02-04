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

from time import sleep
from logging import getLogger

from qpid.messaging import Empty
from qpid.messaging import Disposition, RELEASED, REJECTED

from gofer.messaging.adapter.model import BaseReader, Message
from gofer.messaging.adapter.qpid.reliability import reliable
from gofer.messaging.adapter.qpid.connection import Connection


log = getLogger(__name__)


NO_DELAY = 0.010


class Reader(BaseReader):
    """
    An AMQP message reader.
    :ivar receiver: An AMQP receiver to read.
    :type receiver: qpid.messaging.Receiver
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
        self.connection = Connection(url)
        self.session = None
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
            # already open
            return
        self.connection.open()
        self.session = self.connection.session()
        self.receiver = self.session.receiver(self.queue.name)
    
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

        session = self.session
        self.session = None

        try:
            session.close()
        except Exception:
            pass

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
            return Message(self, impl, impl.content)
        except Empty:
            pass
        except Exception, e:
            log.error(str(e))
            sleep(60)

    def ack(self, message):
        """
        Acknowledge all messages received on the session.
        :param message: The message to acknowledge.
        :type message: qpid.messaging.Message
        """
        self.session.acknowledge(message=message)

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
        self.session.acknowledge(message=message, disposition=disposition)
