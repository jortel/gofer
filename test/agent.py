#! /usr/bin/env python
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

ROOT = '/opt/gofer'

import os
import sys
from time import sleep

# logging
from gofer.agent import logutil
logutil.LOGDIR = ROOT

# lock
from gofer.agent.main import AgentLock
AgentLock.PATH = os.path.join(ROOT, 'gofer.pid')

# pending queue
from gofer.rmi.store import PendingQueue
PendingQueue.ROOT = os.path.join(ROOT, 'messaging/pending')
if not os.path.exists(PendingQueue.ROOT):
    os.makedirs(PendingQueue.ROOT)

# configuration
from gofer.agent.config import Config
Config.PATH = '/opt/gofer/agent.conf'
Config.CNFD = '/opt/gofer/conf.d'

# misc
from gofer.agent.plugin import PluginDescriptor, PluginLoader
from gofer.agent.main import Agent, eager
from logging import getLogger, INFO, DEBUG

log = getLogger(__name__)


def installPlugins(thread):
    root = os.path.dirname(__file__)
    dir = os.path.join(root, 'plugins')
    for fn in os.listdir(dir):
        path = os.path.join(dir, fn)
        if fn.endswith('.conf'):
            pd =  PluginDescriptor(path)
            pd.messaging.threads = threads
            path = os.path.join(PluginDescriptor.ROOT, fn)
            f = open(path, 'w')
            s = str(pd)
            f.write(s)
            f.close()
            continue
        if fn.endswith('.py'):
            f = open(path)
            plugin = f.read()
            f.close()
            path = os.path.join(PluginLoader.PATH[0], fn)
            f = open(path, 'w')
            f.write(plugin)
            f.close()
            continue

def install(threads=1):
    PluginDescriptor.ROOT = os.path.join(ROOT, 'plugins')
    PluginLoader.PATH = [
        os.path.join(ROOT, 'lib/plugins')
    ]
    for path in (PluginDescriptor.ROOT, PluginLoader.PATH[0]):
        if not os.path.exists(path):
            os.makedirs(path)
    installPlugins(threads)
    

class TestAgent:

    def __init__(self, threads):
        install(threads)
        pl = PluginLoader()
        plugins = pl.load(eager())
        agent = Agent(plugins)
        agent.start(False)
        while True:
            sleep(10)
            print 'Agent: sleeping...'


if __name__ == '__main__':
    uuid = 'xyz'
    threads = 3
    if len(sys.argv) > 1:
        threads = int(sys.argv[1])
    if len(sys.argv) > 2:
        uuid = sys.argv[2]
    log.info('started')
    print 'starting agent, threads=%d' % threads
    agent = TestAgent(threads)
