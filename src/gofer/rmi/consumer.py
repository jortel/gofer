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

from gofer.rmi.store import PendingQueue
from gofer.messaging import Consumer, Destination


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
        self.__send_accepted(request)
        pending = PendingQueue()
        pending.add(str(self.url), request)

    def __send_accepted(self, request):
        """
        Send the ACCEPTED status update when requested.
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
            self.transport.plugin.send(endpoint, destination, sn=sn, any=any, status='accepted')
        except Exception:
            log.exception('send (accepted), failed')