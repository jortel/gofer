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

from gofer.messaging.base import Container
from gofer.messaging.producer import Producer
from logging import getLogger

log = getLogger(__name__)


def Agent(uuid, **options):
    """ backwards compat """
    return agent(uuid, **options)

def agent(uuid, **options):
    """
    Get a proxy for the remote Agent.
    @param uuid: An agent ID.
    @type uuid: str
    @return: An agent (proxy).
    @rtype: L{Container}
    """
    url = options.pop('url', None)
    if url:
        p = Producer(url=url)
    else:
        p = Producer()
    return Container(uuid, p, **options)
        
def delete(agent):
    """
    Delete associated AMQP resources.
    @param agent: A gofer agent.
    @type agent: L{Container}
    """
    if isinstance(agent, Container):
        queue = agent._Container__destination()
        method = agent._Container__options.method
        session = method.producer.session()
        queue.delete(session)
    else:
        pass
