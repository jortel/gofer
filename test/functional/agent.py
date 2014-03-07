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

CONFIGURATION = """
[logging]
gofer.agent = info
gofer.messaging = info

[messaging]

[pam]
service = passwd
"""

import os

from time import sleep
from optparse import OptionParser
from logging import getLogger, DEBUG

# logging
from gofer.agent import logutil
logutil.LOGDIR = ROOT

# configuration
from gofer.config import Config
Config.PATH = '/opt/gofer/agent.conf'
Config.CNFD = '/opt/gofer/conf.d'
if not os.path.exists(Config.PATH):
    with open(Config.PATH, 'w+') as fp:
        fp.write(CONFIGURATION)

# lock
from gofer.agent.main import AgentLock
AgentLock.PATH = os.path.join(ROOT, 'gofer.pid')

# pending queue
from gofer.rmi.store import Pending
Pending.PENDING = os.path.join(ROOT, 'messaging/pending')
Pending.DELAYED = os.path.join(ROOT, 'messaging/delayed')

# misc
from gofer.agent.plugin import PluginDescriptor, PluginLoader
from gofer.agent.main import Agent, setup_logging

log = getLogger(__name__)

getLogger('gofer').setLevel(DEBUG)


def install_plugins(url, transport, uuid, threads, auth):
    plugin_configured = False
    root = os.path.dirname(__file__)
    dir = os.path.join(root, 'plugins')
    for fn in os.listdir(dir):
        path = os.path.join(dir, fn)
        if fn.endswith('.conf'):
            conf = Config(path)
            pd = PluginDescriptor(conf)
            if not plugin_configured:
                pd.messaging.url = url
                pd.messaging.transport = transport
                pd.messaging.uuid = uuid
                pd.messaging.threads = threads
                pd.messaging.auth = auth
                plugin_configured = True
            path = os.path.join(PluginDescriptor.ROOT, fn)
            with open(path, 'w') as fp:
                fp.write(str(pd))
            continue
        if fn.endswith('.py'):
            f = open(path)
            plugin = f.read()
            f.close()
            path = os.path.join(PluginLoader.PATH[0], fn)
            with open(path, 'w') as fp:
                fp.write(plugin)
            continue


def install(url, transport, uuid, threads, auth):
    PluginDescriptor.ROOT = os.path.join(ROOT, 'plugins')
    PluginLoader.PATH = [os.path.join(ROOT, 'lib/plugins')]
    for path in (PluginDescriptor.ROOT, PluginLoader.PATH[0]):
        if not os.path.exists(path):
            os.makedirs(path)
    install_plugins(url, transport, uuid, threads, auth)


def get_options():
    parser = OptionParser()
    parser.add_option('-i', '--uuid', default='xyz', help='agent UUID')
    parser.add_option('-u', '--url', help='broker URL')
    parser.add_option('-t', '--threads', default='3', help='number of threads')
    parser.add_option('-T', '--transport', default='qpid', help='transport (qpid|amqplib|rabbitmq)')
    parser.add_option('-a', '--auth', default='', help='enable message auth')
    opts, args = parser.parse_args()
    return opts


class TestAgent:

    def __init__(self, url, transport, uuid, threads, auth):
        setup_logging()
        install(url, transport, uuid, threads, auth)
        plugins = PluginLoader.load()
        agent = Agent(plugins)
        agent.start(False)
        while True:
            sleep(10)
            print 'Agent: sleeping...'


if __name__ == '__main__':
    options = get_options()
    uuid = options.uuid
    url = options.url or 'tcp://localhost:5672'
    threads = int(options.threads)
    transport = options.transport
    auth = options.auth
    print 'starting agent, threads=%d, transport=%s, url=%s' % (threads, transport, url)
    agent = TestAgent(url, transport, uuid, threads, auth)
