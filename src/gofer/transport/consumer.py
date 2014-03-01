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
        Stop processing requests.
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
        Read and process incoming requests.
        """
        try:
            request, ack = self.reader.next(10)
            if request is None:
                return
            self.dispatch(request)
            ack()
        except auth.ValidationFailed, vf:
            self.message_rejected(vf.code, vf.request, vf.details)
        except model.InvalidRequest, ir:
            self.request_rejected(ir.code, ir.request, ir.details)
        except Exception:
            log.exception(self.name)

    def message_rejected(self, code, message, details):
        """
        Called to process the received (invalid) AMQP message.
        This method intended to be overridden by subclasses.
        :param code: The validation code.
        :type code: str
        :param message: The received request.
        :type message: str
        :param details: The explanation.
        :type details: str
        """
        log.debug('%s, reason: %s\n%s', code, details, message)

    def request_rejected(self, code, request, details):
        """
        Called to process the received (invalid) request.
        This method intended to be overridden by subclasses.
        :param code: The validation code.
        :type code: str
        :param request: The received request.
        :type request: Envelope
        :param details: The explanation.
        :type details: str
        """
        log.debug('%s, sn:%s reason:%s\n%s', code, details, request)

    @staticmethod
    def dispatch(request):
        """
        Called to process the received request.
        This method intended to be overridden by subclasses.
        :param request: The received request.
        :type request: Envelope
        """
        log.debug('dispatched:\n%s', request)


class Ack:

    def __init__(self, endpoint, message):
        self.endpoint = endpoint
        self.message = message

    def __call__(self):
        self.endpoint.ack(self.message)