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

from gofer.common import Thread, released
from gofer.messaging.model import DocumentError
from gofer.messaging.adapter.model import Reader


log = getLogger(__name__)


class ConsumerThread(Thread):
    """
    An AMQP (abstract) consumer.
    """

    def __init__(self, queue, url):
        """
        :param queue: An AMQP queue.
        :type queue: gofer.messaging.adapter.model.Queue
        :param url: The broker URL.
        :type url: str
        """
        Thread.__init__(self, name=queue.name)
        self.url = url
        self.queue = queue
        self.authenticator = None
        self._reader = None
        self.setDaemon(True)

    def shutdown(self):
        """
        Shutdown the consumer.
        """
        self.abort()

    @released
    def run(self):
        """
        Main consumer loop.
        """
        self._reader = Reader(self.queue, self.url)
        self._reader.authenticator = self.authenticator
        self._open()
        try:
            while not Thread.aborted():
                self._read()
        finally:
            self._close()

    def _open(self):
        """
        Open the reader.
        """
        while not Thread.aborted():
            try:
                self._reader.open()
                break
            except Exception:
                log.exception(self.getName())
                sleep(60)

    def _close(self):
        """
        Close the reader.
        """
        try:
            self._reader.close()
        except Exception:
            log.exception(self.getName())

    def _read(self):
        """
        Read and process incoming documents.
        """
        try:
            message, document = self._reader.next(10)
            if message is None:
                return
            log.debug('{%s} read: %s', self.getName(), document)
            self.dispatch(document)
            message.ack()
        except DocumentError, de:
            self._rejected(de.code, de.description, de.document, de.details)
        except Exception:
            log.exception(self.getName())
            sleep(60)
            self._close()
            self._open()

    def _rejected(self, code, description, document, details):
        """
        Called to process the received (invalid) document.
        This method intended to be overridden by subclasses.
        :param code: The rejection code.
        :type code: str
        :param description: rejection description
        :type description: str
        :param document: The received *json*  document.
        :type document: str
        :param details: The explanation.
        :type details: str
        """
        log.debug('rejected: %s', document)

    def dispatch(self, document):
        """
        Called to process the received document.
        This method intended to be overridden by subclasses.
        :param document: The received *json*  document.
        :type document: str
        """
        log.debug('dispatched: %s', document)


class Consumer(ConsumerThread):
    """
    An AMQP consumer.
    Thread used to consumer messages from the specified queue.
    On receipt, each message is used to build an document
    and passed to dispatch().
    """

    def __init__(self, queue, url=None):
        """
        :param queue: The AMQP node.
        :type queue: gofer.messaging.adapter.model.Queue
        :param url: The broker URL.
        :type url: str
        """
        super(Consumer, self).__init__(queue, url)
        self.url = url
        self.queue = queue
