#! /usr/bin/env python
#
# Copyright (c) 2010 Red Hat, Inc.
#
# Authors: Jeff Ortel <jortel@redhat.com>
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
#

from gopher.messaging.base import Container
from gopher.messaging.producer import Producer
from logging import getLogger

log = getLogger(__name__)


class Agent(Container):
    """
    A server-side proxy for the remote Agent.
    @ivar __producer: The AMQP producer.
    @type __producer: L{Producer}
    """

    def __init__(self, uuid, producer=None, **options):
        """
        @param uuid: The agent ID.
        @type uuid: str
        @param producer: The AMQP producer.
        @type producer: L{Producer}
        """
        if not producer:
            producer = Producer()
        self.__producer = producer
        Container.__init__(self, uuid, self.__producer, **options)

    def delete(self):
        """
        Delete associated AMQP resources.
        @return: self
        @rtype: L{Agent}
        """
        queue = self._Container__destination()
        if isinstance(queue, (list,tuple)):
            raise Exception, 'not permitted'
        session = self.__producer.session()
        queue.delete(session)
        return self
