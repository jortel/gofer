#! /usr/bin/env python3
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

ROOT = os.path.expanduser('~/.gofer')


from gofer.compat import json

from time import sleep
from optparse import OptionParser
from logging import getLogger
from logging.handlers import RotatingFileHandler

AGENT_CONF = """
[management]
enabled=1
port=5651

[logging]
gofer.agent=info
gofer.messaging=info

[messaging]

"""

from gofer.common import mkdir

# logging
from gofer.agent import logutil

logutil.LogHandler.install()

# configuration
from gofer.agent.config import AgentConfig
mkdir(ROOT)
AgentConfig.PATH = os.path.join(ROOT, 'agent.conf')
if not os.path.exists(AgentConfig.PATH):
    with open(AgentConfig.PATH, 'w+') as fp:
        fp.write(AGENT_CONF)

# lock
from gofer.agent.main import AgentLock
AgentLock.PATH = os.path.join(ROOT, 'gofer.pid')

# pending queue
from gofer.rmi.store import Pending
Pending.PENDING = os.path.join(ROOT, 'messaging/pending')

# tracking
from gofer.rmi.tracker import Canceled
Canceled.PATH = os.path.join(ROOT, 'messaging/canceled')

# misc
from gofer.agent.plugin import PluginDescriptor, PluginLoader
from gofer.agent.main import Agent, setup_logging
from gofer.config import Config

# getLogger('gofer').setLevel(DEBUG)

log_path = os.path.join(ROOT, 'agent.log')
log_handler = RotatingFileHandler(log_path, maxBytes=0x100000, backupCount=5)
log_handler.setFormatter(logutil.FORMATTER)
root = getLogger()
root.addHandler(log_handler)


def install_plugins(url, uuid, threads, auth, exchange):
    root = os.path.dirname(__file__)
    _dir = os.path.join(root, 'plugins')
    for fn in os.listdir(_dir):
        path = os.path.join(_dir, fn)
        _, ext = os.path.splitext(path)
        if ext in ('.conf', '.json'):
            conf = Config(path)
            pd = PluginDescriptor(conf)
            if pd.messaging.uuid == 'TEST':
                pd.main.threads = threads
                pd.messaging.url = url
                pd.messaging.uuid = uuid
                pd.messaging.auth = auth
            if exchange:
                pd.messaging.exchange = exchange
            path = os.path.join(PluginDescriptor.ROOT, fn)
            with open(path, 'w') as fp:
                if ext == '.conf':
                    fp.write(str(pd))
                else:
                    json.dump(conf, fp, indent=4)
            continue
        if fn.endswith('.py'):
            f = open(path)
            plugin = f.read()
            f.close()
            path = os.path.join(PluginLoader.PATH[0], fn)
            with open(path, 'w') as fp:
                fp.write(plugin)
            continue


def install(url, uuid, threads, auth, exchange):
    PluginDescriptor.ROOT = os.path.join(ROOT, 'plugins')
    PluginLoader.PATH = [os.path.join(ROOT, 'lib/plugins')]
    for path in (PluginDescriptor.ROOT, PluginLoader.PATH[0]):
        if not os.path.exists(path):
            os.makedirs(path)
    install_plugins(url, uuid, threads, auth, exchange)


def get_options():
    parser = OptionParser()
    parser.add_option('-i', '--uuid', default='xyz', help='agent UUID')
    parser.add_option('-u', '--url', help='broker URL')
    parser.add_option('-t', '--threads', default='3', help='number of threads')
    parser.add_option('-a', '--auth', default='', help='enable message auth')
    parser.add_option('-e', '--exchange', default='', help='exchange')
    opts, args = parser.parse_args()
    return opts


class TestAgent:

    def __init__(self, url, uuid, threads, auth, exchange):
        setup_logging()
        install(url, uuid, threads, auth, exchange)
        PluginLoader.load_all()
        agent = Agent()
        agent.start(False)
        while True:
            sleep(10)
            print('Agent: sleeping...')


if __name__ == '__main__':
    options = get_options()
    uuid = options.uuid
    url = options.url or 'tcp://localhost:5672'
    threads = int(options.threads)
    auth = options.auth
    exchange = options.exchange
    print('starting agent, pid=%d, threads=%d, url=%s' % (os.getpid(), threads, url))
    agent = TestAgent(url, uuid, threads, auth, exchange)
