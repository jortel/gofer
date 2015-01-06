# Copyright (c) 2014 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from unittest import TestCase

from mock import patch

from gofer import Options
from gofer.proxy import Agent, agent
from gofer.rmi.container import Container


class TestProxy(TestCase):

    def test_init(self):
        url = 'qpid+amqp://host'
        route = 'xyz'
        options = {'A': 1, 'B': 2}
        _agent = Agent(url, route, **options)
        _options = Options(options)
        self.assertTrue(_agent, Container)
        self.assertEqual(_agent._Container__url, url)
        self.assertEqual(_agent._Container__route, route)
        self.assertEqual(_agent._Container__options.__dict__, _options.__dict__)

    @patch('gofer.proxy.Agent')
    def test_agent(self, _agent):
        url = 'qpid+amqp://host'
        route = 'xyz'
        options = {'A': 1, 'B': 2}
        proxy = agent(url, route, **options)
        _agent.assert_called_with(url, route, **options)
        self.assertEqual(proxy, _agent.return_value)