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

from gofer.messaging import auth
from gofer.messaging import model
from gofer.messaging.model import Document
from gofer.messaging.adapter.model import BaseReader, Ack
from gofer.messaging.adapter.qpid.endpoint import Endpoint


log = getLogger(__name__)


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
        BaseReader.open(self)
        channel = self.channel()
        self._receiver = channel.receiver(self.queue.name)
    
    def close(self, hard=False):
        """
        Close the reader.
        :param hard: Force the connection closed.
        :type hard: bool
        """
        self._receiver.close()
        BaseReader.close(self, hard)

    def get(self, timeout=None):
        """
        Get the next message.
        :param timeout: The read timeout.
        :type timeout: int
        :return: The next message, or (None).
        :rtype: qpid.messaging.Message
        """
        try:
            return self._receiver.fetch(timeout=timeout)
        except Empty:
            pass
        except Exception:
            log.error(self.id(), exc_info=1)
            sleep(10)

    def next(self, timeout=90):
        """
        Get the next document from the queue.
        :param timeout: The read timeout.
        :type timeout: int
        :return: A tuple of: (document, ack())
        :rtype: (Document, callable)
        :raises: model.InvalidDocument
        """
        message = self.get(timeout)
        if message:
            try:
                document = auth.validate(self.authenticator, message.content)
                document.subject = subject(message)
                document.ttl = message.ttl
                model.validate(document)
            except model.InvalidDocument:
                self.ack(message)
                raise
            log.debug('read next: %s', document)
            return document, Ack(self, message)
        return None, None
