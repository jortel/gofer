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

from gofer.rmi.container import Container
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
