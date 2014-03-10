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


from threading import Thread
from logging import getLogger

from gofer.messaging import auth
from gofer.messaging import model


log = getLogger(__name__)


class Consumer(Thread):
    """
    An AMQP (abstract) consumer.
    """

    def __init__(self, reader):
        """
        :param reader: An AMQP queue reader.
        :type reader: gofer.transport.model.Reader
        """
        Thread.__init__(self, name=reader.queue.name)
        self.reader = reader
        self._run = True
        self.setDaemon(True)

    def stop(self):
        """
        Stop processing documents.
        """
        self._run = False

    def run(self):
        """
        Main consumer loop.
        """
        self.reader.open()
        try:
            while self._run:
                self.__read()
        finally:
            self.reader.close()

    def __read(self):
        """
        Read and process incoming documents.
        """
        try:
            document, ack = self.reader.next(10)
            if document is None:
                return
            log.debug('{%s} read:\n%s', self.name, document)
            self.dispatch(document)
            ack()
        except auth.ValidationFailed, vf:
            self.message_rejected(vf.code, vf.document, vf.details)
        except model.InvalidDocument, ir:
            self.document_rejected(ir.code, ir.document, ir.details)
        except Exception:
            log.exception(self.name)

    def message_rejected(self, code, message, details):
        """
        Called to process the received (invalid) AMQP message.
        This method intended to be overridden by subclasses.
        :param code: The validation code.
        :type code: str
        :param message: The received document.
        :type message: str
        :param details: The explanation.
        :type details: str
        """
        log.debug('%s, reason: %s\n%s', code, details, message)

    def document_rejected(self, code, document, details):
        """
        Called to process the received (invalid) document.
        This method intended to be overridden by subclasses.
        :param code: The validation code.
        :type code: str
        :param document: The received document.
        :type document: Document
        :param details: The explanation.
        :type details: str
        """
        log.debug('%s, sn:%s reason:%s\n%s', code, details, document)

    @staticmethod
    def dispatch(document):
        """
        Called to process the received document.
        This method intended to be overridden by subclasses.
        :param document: The received document.
        :type document: Document
        """
        log.debug('dispatched:\n%s', document)


class Ack:

    def __init__(self, endpoint, message):
        self.endpoint = endpoint
        self.message = message

    def __call__(self):
        self.endpoint.ack(self.message)