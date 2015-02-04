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


class Agent(Container):
    """
    A remote agent.
    """

    def __init__(self, url, address, **options):
        """
        :param url: The agent URL.
        :type url: str
        :param address: The AMQP address to the agent.
        :type address: str
        """
        super(Agent, self).__init__(url, address, **options)


def agent(url, address, **options):
    """
    Get a proxy for the remote Agent.
    :param url: The agent URL.
    :type url: str
    :param address: The AMQP address to the agent.
    :type address: str
    :return: An agent (proxy).
    :rtype: Agent
    """
    return Agent(url, address, **options)
