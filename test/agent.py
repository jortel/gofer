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

import os
import sys
from time import sleep
from gofer.agent.config import Config
Config.PATH = '/opt/gofer/agent.conf'
Config.CNFD = '/opt/gofer/conf.d'
from gofer.messaging import Queue
from gofer.decorators import *
from gofer.rmi.consumer import RequestConsumer
from gofer.messaging.broker import Broker
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
    PluginDescriptor.ROOT = '/opt/gofer/plugins'
    PluginLoader.PATH = ['/opt/gofer/lib/plugins']
    for path in (PluginDescriptor.ROOT, PluginLoader.PATH[0]):
        if not os.path.exists(path):
            os.makedirs(path)
    installPlugins(threads)
    

class TestAgent:
    def __init__(self, uuid, threads):
        install(threads)
        url = 'ssl://localhost:5674'
        url = 'tcp://50.17.201.180:5672'
        url = 'tcp://localhost:5672'
        broker = Broker(url)
        broker.cacert = '/etc/pki/qpid/ca/ca.crt'
        broker.clientcert = '/etc/pki/qpid/client/client.pem'
        pl = PluginLoader()
        plugins = pl.load(eager())
        agent = Agent(plugins)
        agent.start(False)
        while True:
            sleep(10)
            print 'Agent: sleeping...'

if __name__ == '__main__':
    uuid = 'xyz'
    threads = 1
    if len(sys.argv) > 1:
        threads = int(sys.argv[1])
    if len(sys.argv) > 2:
        uuid = sys.argv[2]
    log.info('started')
    print 'starting agent (%s), threads=%d' % (uuid, threads)
    agent = TestAgent(uuid, threads)
