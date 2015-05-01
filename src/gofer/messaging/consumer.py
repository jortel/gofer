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
from gofer.messaging.model import InvalidDocument
from gofer.messaging.adapter.model import Reader


log = getLogger(__name__)


class ConsumerThread(Thread):
    """
    An AMQP (abstract) consumer.
    """

    def __init__(self, node, url, wait=3):
        """
        :param node: An AMQP queue.
        :type node: gofer.messaging.adapter.model.Node
        :param url: The broker URL.
        :type url: str
        :param wait: Number of seconds to wait for a message.
        :type wait: int
        """
        Thread.__init__(self, name=node.name)
        self.url = url
        self.node = node
        self.wait = wait
        self.authenticator = None
        self.reader = None
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
        self.reader = Reader(self.node, self.url)
        self.reader.authenticator = self.authenticator
        self.open()
        try:
            while not Thread.aborted():
                self.read()
        finally:
            self.close()

    def open(self):
        """
        Open the reader.
        """
        while not Thread.aborted():
            try:
                self.reader.open()
                break
            except Exception:
                log.exception(self.getName())
                sleep(30)

    def close(self):
        """
        Close the reader.
        """
        try:
            self.reader.close()
        except Exception:
            log.exception(self.getName())

    def read(self):
        """
        Read and process incoming documents.
        """
        try:
            wait = self.wait
            reader = self.reader
            message, document = reader.next(wait)
            if message is None:
                # wait expired
                return
            log.debug('{%s} read: %s', self.getName(), document)
            self.dispatch(document)
            message.ack()
        except InvalidDocument, invalid:
            self.rejected(invalid.code, invalid.description, invalid.document, invalid.details)
        except Exception:
            log.exception(self.getName())
            sleep(60)
            self.close()
            self.open()

    def rejected(self, code, description, document, details):
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

    def __init__(self, node, url=None):
        """
        :param node: The AMQP node.
        :type node: gofer.messaging.adapter.model.Node
        :param url: The broker URL.
        :type url: str
        """
        super(Consumer, self).__init__(node, url)
