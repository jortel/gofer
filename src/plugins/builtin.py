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
        log.info('Hello:\n%s', cfg)


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
    
    @remotemethod
    def help(self):
        s = []
        s.append('plugins:')
        for p in Plugin.descriptor.keys():
            s.append('  %s' % p)
        s.append('actions:')
        for a in Action.actions:
            s.append('  %s %s' % a)
        s.append('methods:')
        for m in self.__methods():
            s.append('  %s.%s()' % m)
        return '\n'.join(s)
    
    def __methods(self):
        methods = []
        for c in Remote.classes:
            for m in dir(c):
                m = getattr(c, m)
                if callable(m) and m.im_func in Remote.methods:
                    methods.append((c, m.__name__))
        return methods


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
#class MyIdentity:
#    def getuuid(self):
#        return 'zzz'