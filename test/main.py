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

"""
Provides a debugging agent that loads configuration and plugins
from standard locations.  But, does not need to run as root
since it does use /var directories.
IMPORTANT: be sure the installed daemon is stopped.
"""

import os
import time
import shutil

from tempfile import mkdtemp
from optparse import OptionParser
from multiprocessing import Process


# --- utils ------------------------------------------------------------------

def mkdir(path):
    if not os.path.exists(path):
        os.makedirs(path)
    return path


# --- agent ------------------------------------------------------------------


class TestAgent:

    def __init__(self, root=None):
        self.root = root or mkdtemp()

    def start(self, spoofing=None):
        self._setup_logging()
        self._setup_spoofing(spoofing)
        self._setup_locking()
        self._setup_pending_queue()

        from gofer.agent.main import PluginLoader, Agent

        pl = PluginLoader()
        plugins = pl.load()
        agent = Agent(plugins)
        agent.start(False)
        print 'Agent pid:%s started. Working directory [ %s ]' % (os.getpid(), self.root)
        while True:
            time.sleep(10)

    def _setup_logging(self):
        from gofer.agent import logutil
        logutil.LOGDIR = os.path.join(self.root, 'var/log/gofer')
        mkdir(logutil.LOGDIR)

    def _setup_locking(self):
        from gofer.agent.main import AgentLock
        lock_dir = 'var/lock'
        AgentLock.PATH = os.path.join(self.root, lock_dir, 'gofer.pid')
        mkdir(lock_dir)

    def _setup_pending_queue(self):
        from gofer.rmi.store import PendingQueue
        PendingQueue.ROOT = os.path.join(self.root, 'messaging/pending')
        mkdir(PendingQueue.ROOT)

    def _setup_spoofing(self, suffix):
        from gofer.agent.plugin import Plugin
        if suffix:
            impl = Plugin.get_uuid
            def get_uuid(plugin):
                uuid = impl(plugin)
                if uuid:
                    uuid = '-'.join((uuid, suffix))
                return uuid
            Plugin.get_uuid = get_uuid


# --- python scripting -------------------------------------------------------


def main(working_dir=None, background=False, spoofing=None):
    def run():
        agent = TestAgent(working_dir)
        agent.start(spoofing)
        if not working_dir:
            shutil.rmtree(agent.root, ignore_errors=True)
        print 'Done'
    if background:
        p = Process(target=run)
        p.daemon = True
        p.start()
        return p.pid
    else:
        run()


# --- shell scripting --------------------------------------------------------


SUFFIX = '(optional) plugin uuid suffix; used for uuid spoofing'
DIR = '(optional) agent working directory'
BG = 'run in the background'

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option('-s', dest='suffix', help=SUFFIX)
    parser.add_option('-d', dest='dir', help=DIR, default=None)
    parser.add_option('--bg', dest='background', help=BG, action='store_true', default=False)
    options, args = parser.parse_args()
    main(working_dir=options.dir, background=options.background, spoofing=options.suffix)
