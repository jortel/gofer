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

from time import sleep
from logging import getLogger

from gofer.messaging import Node, Consumer, Producer, Document, NotFound
from gofer.metrics import timestamp

log = getLogger(__name__)


class RequestConsumer(Consumer):
    """
    Request consumer.
    Reads messages from AMQP, sends the accepted status then writes
    to local pending queue to be consumed by the scheduler.
    """

    def __init__(self, plugin, model):
        """
        :param model: An AMQP node.
        :type model: gofer.agent.plugin.BrokerModel
        """
        super(RequestConsumer, self).__init__(Node(model.queue), plugin.url)
        self.plugin = plugin
        self.model = model

    @property
    def scheduler(self):
        return self.plugin.scheduler

    def repair(self, error):
        """
        Repair the consumer.
        :param error: The caught exception.
        :type  error: Exception
        """
        try:
            raise error
        except NotFound:
            self.close()
            self.model.setup()
            self.open()
        except Exception:
            log.exception(self.getName())
            sleep(10)
            super(RequestConsumer, self).repair(error)

    def rejected(self, code, description, document, details):
        """
        Called to process the received (invalid) document.
        This method intended to be overridden by subclasses.
        :param code: The rejection code.
        :type code: str
        :param description: rejection description
        :type description: str
        :param document: The received document.
        :type document: Document
        :param details: The explanation.
        :type details: str
        """
        details = dict(
            code=code,
            description=description,
            details=details)
        self.send(document, 'rejected', **details)

    def send(self, request, status, **details):
        """
        Send a status update.
        :param request: The received (json) request.
        :type request: Document
        :param status: The status to send ('accepted'|'rejected')
        :type status: str
        """
        address = request.replyto
        if not address:
            return
        try:
            producer = Producer(self.url)
            producer.authenticator = self.authenticator
            producer.open()
            try:
                producer.send(
                    address,
                    sn=request.sn,
                    data=request.data,
                    status=status,
                    timestamp=timestamp(),
                    **details)
            finally:
                producer.close()
        except Exception:
            log.exception('send (%s), failed', status)

    def dispatch(self, request):
        """
        Dispatch received request.
        Update the request: inject the inbound_url.
        :param request: The received request.
        :type request: Document
        """
        self.send(request, 'accepted')
        self.scheduler.add(request)
