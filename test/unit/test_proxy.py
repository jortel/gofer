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

from mock import patch, Mock

from gofer import Options
from gofer.proxy import Agent, agent
from gofer.rmi.container import Container


class TestProxy(TestCase):

    def test_init(self):
        uuid = 'xyz'
        window = Mock()
        options = {'url': 'qpid+amqp://host', 'A': 1, 'B': 2, 'window': window}
        _agent = Agent(uuid, **options)
        url = options.pop('url')
        _options = Options(window=window)
        _options += options
        self.assertTrue(_agent, Container)
        self.assertEqual(_agent._Container__id, uuid)
        self.assertEqual(_agent._Container__url, url)
        self.assertEqual(_agent._Container__route, uuid)
        self.assertEqual(_agent._Container__options.__dict__, _options.__dict__)

    @patch('gofer.rmi.container.Window')
    def test_init_defaults(self, window):
        uuid = 'xyz'

        options = {'url': 'qpid+amqp://host', 'A': 1, 'B': 2}
        _agent = Agent(uuid, **options)
        url = options.pop('url')
        _options = Options(window=window.return_value)
        _options += options
        self.assertTrue(_agent, Container)
        self.assertEqual(_agent._Container__id, uuid)
        self.assertEqual(_agent._Container__url, url)
        self.assertEqual(_agent._Container__route, uuid)
        self.assertEqual(_agent._Container__options.__dict__, _options.__dict__)

    @patch('gofer.proxy.Agent')
    def test_agent(self, _agent):
        uuid = 'xyz'
        options = {'url': 'amqp://host', 'A': 1, 'B': 2}
        proxy = agent(uuid, **options)
        _agent.assert_called_with(uuid, **options)
        self.assertEqual(proxy, _agent.return_value)