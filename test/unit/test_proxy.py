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

from gofer.proxy import Agent, agent


class Test(TestCase):

    @patch('gofer.proxy.Container')
    def test_agent_1(self, fake_container):
        uuid = 'xyz'
        options = {'url': 'amqp://host', 'transport': 'qpid', 'A': 1, 'B': 2}
        container = Agent(uuid, **options)
        url = options.pop('url')
        transport = options.pop('transport')
        fake_container.assert_called_with(uuid, url, transport, **options)
        self.assertEqual(container, fake_container())

    @patch('gofer.proxy.Container')
    def test_agent(self, fake_container):
        uuid = 'xyz'
        options = {'url': 'amqp://host', 'transport': 'qpid', 'A': 1, 'B': 2}
        container = agent(uuid, **options)
        url = options.pop('url')
        transport = options.pop('transport')
        fake_container.assert_called_with(uuid, url, transport, **options)
        self.assertEqual(container, fake_container())