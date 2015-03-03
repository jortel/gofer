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

from uuid import uuid4
from unittest import TestCase

from mock import patch

from gofer.agent.config import AgentConfig, AGENT_SCHEMA, AGENT_DEFAULTS, Graph


class TestAgentConfig(TestCase):

    @patch('gofer.agent.config.Config')
    def test_init(self, cfg):
        path = str(uuid4())
        agent = AgentConfig(path)
        cfg.assert_called_once_with(AGENT_DEFAULTS, path)
        cfg.return_value.validate.assert_called_once_with(AGENT_SCHEMA)
        self.assertTrue(isinstance(agent, Graph))