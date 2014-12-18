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

from gofer.messaging.adapter.model import BaseReader, Message
from gofer.messaging.adapter.qpid.endpoint import Endpoint


log = getLogger(__name__)


NO_DELAY = 0.0010


# --- utils ------------------------------------------------------------------


def subject(message):
    """
    Extract the message subject.
    :param message: The received message.
    :type message: qpid.messaging.Message
    :return: The message subject
    :rtype: str
    """
    return message.properties.get('qpid.subject')


# --- consumers --------------------------------------------------------------


class Reader(BaseReader):
    """
    An AMQP message reader.
    :ivar _receiver: An AMQP receiver to read.
    :type _receiver: qpid.messaging.Receiver
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
        self.queue = queue
        self._receiver = None
        self._endpoint = Endpoint(url)

    def endpoint(self):
        """
        Get a concrete object.
        :return: A concrete object.
        :rtype: BaseEndpoint
        """
        return self._endpoint

    def open(self):
        """
        Open the reader.
        """
        if self.is_open():
            # already open
            return
        BaseReader.open(self)
        channel = self.channel()
        self._receiver = channel.receiver(self.queue.name)
    
    def close(self, hard=False):
        """
        Close the reader.
        :param hard: Force the connection closed.
        :type hard: bool
        """
        if not self.is_open():
            # not open
            return
        self._receiver.close()
        BaseReader.close(self, hard)

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
            return Message(self, impl, impl.content)
        except Empty:
            pass
        except Exception, e:
            log.error(str(e))
            sleep(60)
