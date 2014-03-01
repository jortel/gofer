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

from logging import getLogger

from gofer.rmi.store import Pending
from gofer.messaging import Consumer, Destination
from gofer.messaging.model import Envelope
from gofer.constants import ACCEPTED, REJECTED

log = getLogger(__name__)


class RequestConsumer(Consumer):
    """
    Request consumer.
    Reads messages from AMQP, sends the accepted status then writes
    to local pending queue to be consumed by the scheduler.
    """

    def dispatch(self, request):
        """
        Dispatch received request.
        :param request: The received request.
        :type request: Envelope
        """
        self.__send_status(request, ACCEPTED)
        pending = Pending()
        pending.put(request)

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
        request = Envelope()
        request.load(message)
        self.__send_status(request, REJECTED, code=code, details=details)

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
        self.__send_status(request, REJECTED, code=code, details=details)

    def __send_status(self, request, status, **details):
        """
        Send a status update.
        :param status: The status to send ('accepted'|'rejected')
        :type status: str
        :param request: The received request.
        :type request: Envelope
        """
        sn = request.sn
        any = request.any
        replyto = request.replyto
        if not replyto:
            return
        try:
            endpoint = self.reader
            destination = Destination.create(replyto)
            self.transport.plugin.send(
                endpoint, destination, sn=sn, any=any, status=status, **details)
        except Exception:
            log.exception('send (%s), failed', status)
