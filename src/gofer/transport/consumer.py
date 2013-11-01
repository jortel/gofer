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


log = getLogger(__name__)


class Consumer(Thread):
    """
    An AMQP (abstract) consumer.
    """

    def __init__(self, reader):
        """
        :param reader: An AMQP queue reader.
        :type reader: Reader
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
        self.reader.open()
        try:
            while self._run:
                envelope, ack = self.reader.next(10)
                if envelope is None:
                    continue
                try:
                    self.dispatch(envelope)
                    ack()
                except Exception:
                    log.exception(self.name)
        finally:
            self.reader.close()

    def dispatch(self, envelope):
        """
        Called to process the received envelope.
        This method intended to be overridden by subclasses.
        :param envelope: The received envelope.
        :type envelope: Envelope
        """
        log.debug('{%s} dispatched:\n%s', self.name, envelope)


class Ack:

    def __init__(self, endpoint, message):
        self.endpoint = endpoint
        self.message = message

    def __call__(self):
        self.endpoint.ack(self.message)