#
# Copyright (c) 2010 Red Hat, Inc.
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

"""
Demo plugin.
"""
import os
from gopher import Plugin
from gopher.agent.action import Action
from gopher.decorators import *
from gopher.agent.config import Config
from logging import getLogger

log = getLogger(__name__)


@action(minutes=10)
class TestAction(Action):

    def perform(self):
        cfg = Plugin.cfg(__name__)
        log.info('Hello:\n%s', cfg)#


@remote
@alias(name='admin')
class AgentAdmin:

    @remotemethod
    def hello(self):
        s = []
        cfg = Config()
        s.append('Hello, I am gopher agent "%s"' % cfg.main.uuid)
        s.append('Here is my configuration:\n%s' % cfg)
        s.append('Status: ready')
        return '\n'.join(s)


@remote
@alias(name='shell')
class Shell:

    @remotemethod
    def run(self, cmd):
        """
        Run a shell command.
        @param cmd: The command & arguments.
        @type cmd: str
        @return: The command output.
        @rtype: str
        """
        f = os.popen(cmd)
        try:
            return f.read()
        finally:
            f.close()


#@identity
#def getuuid():
#    return '123'