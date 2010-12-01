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
import socket
from gofer.decorators import *
from gofer.collator import Collator
from gofer.messaging.decorators import Remote
from gofer.agent.plugin import Plugin
from gofer.agent.action import Actions
from gofer.agent.config import Config
from logging import getLogger

log = getLogger(__name__)


class TestAction:

    @action(minutes=10)
    def hello(self):
        plugin = Plugin.find(__name__)
        log.info('Hello:\n%s', plugin.cfg())


class Admin:

    @remote
    def hello(self):
        s = []
        cfg = Config()
        s.append('Hello, I am gofer agent "%s"' % socket.gethostname())
        s.append('Here is my configuration:\n%s' % cfg)
        s.append('Status: ready')
        return '\n'.join(s)
    
    @remote
    def help(self):
        s = []
        s.append('Plugins:')
        for p in Plugin.all():
            if p.synonyms:
                s.append('  %s %s' % (p.name, p.synonyms))
            else:
                s.append('  %s' % p.name)
        s.append('Actions:')
        for a in self.__actions():
            s.append('  %s %s' % a)
        methods, functions = self.__remote()
        s.append('Methods:')
        for m in methods:
            s.append('  %s.%s()' % m)
        s.append('Functions:')
        for m in functions:
            s.append('  %s.%s()' % m)
        return '\n'.join(s)
    
    def __actions(self):
        actions = []
        for a in Actions().collated():
            actions.append((a.name(), a.interval))
        return actions
    
    def __remote(self):
        methods = []
        funclist = []
        c = Collator()
        classes, functions = c.collate(Remote.functions)
        for n,v in classes.items():
            for m,d in v:
                methods.append((n.__name__, m.__name__))
        for n,v in functions.items():
            for f,d in v:
                funclist.append((n.__name__, f.__name__))
        methods.sort()
        funclist.sort()
        return (methods, funclist)


class Shell:

    @remote
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
            
            
@remote
def echo(something):
    return something


#@identity
#def getuuid():
#    return 'zzz'

#class Identity:    
#    @identity
#    def getuuid(self):
#        return 'yyy'