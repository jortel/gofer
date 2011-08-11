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

from gofer.rmi.store import PendingQueue
from gofer.messaging.consumer import Consumer
from logging import getLogger

log = getLogger(__name__)


class RequestConsumer(Consumer):
    """
    Reply consumer.
    Reads messages from AMQP and writes to
    local pending queue to be consumed by the scheduler.
    """

    def dispatch(self, envelope):
        """
        Dispatch received request.
        @param envelope: The received envelope.
        @type envelope: L{Envelope}
        """
        url = str(self.url)
        pending = PendingQueue()
        pending.add(url, envelope)