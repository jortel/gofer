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

"""
Builtin plugin.
"""
import os
import socket
import inspect
from uuid import uuid4
from gofer.decorators import *
from gofer.agent.plugin import Plugin
from gofer.agent.action import Actions
from gofer.agent.config import Config
from logging import getLogger

log = getLogger(__name__)
plugin = Plugin.find(__name__)


def indent(v, n, *args):
    s = []
    for n in range(0,n):
        s.append(' ')
    s.append(str(v) % args)
    return ''.join(s)


class TestAction:

    @action(hours=36)
    def hello(self):
        plugin = Plugin.find(__name__)
        log.info('Hello:\n%s', plugin.cfg())


class Admin:

    @remote
    def hello(self):
        s = []
        cfg = Config()
        s.append('Hello, I am gofer agent "%s"' % plugin.getuuid())
        s.append('Here is my configuration:\n%s' % cfg)
        s.append('Status: ready')
        return '\n'.join(s)
    
    @remote
    def help(self):
        s = []
        s.append('Plugins:')
        for p in Plugin.all():
            # plugin
            s.append('')
            if p.synonyms:
                s.append(indent('<plugin> %s %s', 2, p.name, p.synonyms))
            else:
                s.append(indent('<plugin> %s', 2, p.name))
            # classes
            s.append(indent('Classes:', 4))
            for n,v in p.dispatcher.classes.items():
                if inspect.ismodule(v):
                    continue
                s.append(indent('<class> %s', 6, n))
                s.append(indent('methods:', 8))
                for n,v in inspect.getmembers(v, inspect.ismethod):
                    fn = v.im_func
                    if not hasattr(fn, 'gofer'):
                        continue
                    s.append(indent(self.__signature(n, fn), 10))
            # functions
            s.append(indent('Functions:', 4))
            for n,v in p.dispatcher.classes.items():
                if not inspect.ismodule(v):
                    continue
                for n,v in inspect.getmembers(v, inspect.isfunction):
                    fn = v
                    if not hasattr(fn, 'gofer'):
                        continue
                    s.append(indent(self.__signature(n, fn), 6))
        s.append('')
        s.append('Actions:')
        for a in self.__actions():
            s.append('  %s %s' % a)
        return '\n'.join(s)
    
    def __actions(self):
        actions = []
        for a in Actions().collated():
            actions.append((a.name(), a.interval))
        return actions
    
    def __signature(self, n, fn):
        s = []
        s.append(n)
        s.append('(')
        spec = inspect.getargspec(fn)
        if 'self' in spec[0]:
            spec[0].remove('self')
        if spec[1]:
            spec[0].append('*%s' % spec[1])
        if spec[2]:
            spec[0].append('**%s' % spec[2])
        s.append(', '.join(spec[0]))
        s.append(')')
        return ''.join(s)
            
            
@remote
def echo(something):
    return something

#
# Set the uuid to the hostname when not
# specified in the config.
#
if not plugin.getuuid():
    hostname = socket.gethostname()
    uuid = str(uuid4())
    if not hostname.startswith('localhost'):
        uuid = 'admin@%s' % hostname
    plugin.setuuid(uuid)
