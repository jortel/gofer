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

from gofer.agent import logutil


class TestAgent:

    ROOT = '/tmp/gofer'

    def start(self):
        self.mkdir()
        logutil.LOGDIR = self.ROOT

        from gofer.agent.main import PluginLoader, Agent, AgentLock, eager
        from gofer.rmi.store import PendingQueue

        AgentLock.PATH = os.path.join(self.ROOT, 'gofer.pid')
        PendingQueue.ROOT = os.path.join(self.ROOT, 'messaging/pending')
        self.mkdir(PendingQueue.ROOT)

        pl = PluginLoader()
        plugins = pl.load(eager())
        agent = Agent(plugins)
        agent.start(False)
        print 'Agent: started'
        while True:
            time.sleep(10)
            print 'Agent: sleeping...'

    def mkdir(self, path=ROOT):
        if not os.path.exists(path):
            os.makedirs(path)
        return path


if __name__ == '__main__':
    agent = TestAgent()
    agent.start()
    print 'Done'