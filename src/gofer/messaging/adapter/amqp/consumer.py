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

from logging import getLogger

from gofer.messaging.adapter.model import BaseReader, Message
from gofer.messaging.adapter.decorators import blocking
from gofer.messaging.adapter.amqp.endpoint import Endpoint, reliable


log = getLogger(__name__)


class Reader(BaseReader):
    """
    An AMQP message reader.
    :ivar queue: The AMQP queue to read.
    :type queue: gofer.messaging.adapter.model.Queue
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
        self._endpoint = Endpoint(url)

    def endpoint(self):
        """
        Get a concrete object.
        :return: A concrete object.
        :rtype: BaseEndpoint
        """
        return self._endpoint

    @blocking
    @reliable
    def get(self, timeout=None):
        """
        Get the next message from the queue.
        :param timeout: The read timeout in seconds.
        :type timeout: int
        :return: The next message or None.
        :rtype: Message
        """
        channel = self.channel()
        impl = channel.basic_get(self.queue.name)
        if impl:
            return Message(self, impl, impl.body)
        else:
            return None
