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

from gofer.transport.model import Reader

from gofer.transport.consumer import Consumer as BaseConsumer


class Consumer(BaseConsumer):
    """
    An AMQP consumer.
    Thread used to consumer messages from the specified queue.
    On receipt, each message is used to build an document
    and passed to dispatch().
    """

    def __init__(self, queue, url=None):
        """
        :param queue: The AMQP node.
        :type queue: gofer.transport.model.Queue
        :param url: The broker URL.
        :type url: str
        """
        BaseConsumer.__init__(self, Reader(queue, url=url))
        self.url = url
        self.queue = queue
        queue.declare(url)
