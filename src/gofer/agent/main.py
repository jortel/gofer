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

import sys
import os
import logging

from time import sleep
from getopt import getopt, GetoptError

from gofer.agent.logutil import LogHandler

LogHandler.install()

from gofer import NAME
from gofer import pam
from gofer.common import Thread, released
from gofer.config import get_bool
from gofer.agent.plugin import Plugin, PluginLoader
from gofer.agent.manager import Manager
from gofer.agent.lock import Lock, LockFailed
from gofer.agent.config import AgentConfig

log = logging.getLogger(__name__)


class ActionThread(Thread):
    """
    Run actions independently of main thread.
    """
    
    def __init__(self):
        Thread.__init__(self, name='Actions')
        self.setDaemon(True)

    @released
    def run(self):
        """
        Run actions.
        """
        while not Thread.aborted():
            for plugin in Plugin.all():
                for action in plugin.actions:
                    plugin.pool.run(action)
            sleep(10)


class Agent:
    """
    Gofer (main) agent.
    Starts (2) threads.  A thread to run actions and
    another to monitor/update plugin sessions on the bus.
    """

    WAIT = None

    def __init__(self):
        cfg = AgentConfig()
        pam.SERVICE = cfg.pam.service

    def start(self, block=True):
        """
        Start the agent.
        """
        cfg = AgentConfig()
        for plugin in Plugin.all():
            plugin.start()
        if get_bool(cfg.manager.enabled):
            host = cfg.manager.host
            port = int(cfg.manager.port)
            manager = Manager(host, port)
            manager.start()
        actions = ActionThread()
        actions.start()
        log.info('agent started.')
        if block:
            actions.join(self.WAIT)


class AgentLock(Lock):
    """
    Agent lock ensure that agent only has single instance running.
    :cvar PATH: The lock file absolute path.
    :type PATH: str
    """

    PATH = '/var/run/%sd.pid' % NAME

    def __init__(self):
        Lock.__init__(self, self.PATH)


def start(daemon=True):
    """
    Agent main.
    Add recurring, time-based actions here.
    All actions must be subclass of action.Action.
    """
    lock = AgentLock()
    try:
        lock.acquire(False)
    except LockFailed:
        raise Exception('Agent already running')
    if daemon:
        start_daemon(lock)
    try:
        PluginLoader.load_all()
        agent = Agent()
        agent.start()
    finally:
        lock.release()


def usage():
    """
    Show usage.
    """
    s = list()
    s.append('\n%sd <options>' % NAME)
    s.append('  -h, --help')
    s.append('      Show help')
    s.append('  -f, --foreground')
    s.append('      Run in the foreground and not as a daemon.')
    s.append('\n')
    print '\n'.join(s)


def start_daemon(lock):
    """
    Daemon configuration.
    """
    pid = os.fork()
    if pid == 0:  # child
        os.setsid()
        os.chdir('/')
        os.close(0)
        os.close(1)
        os.close(2)
        fp = os.open('/dev/null', os.O_RDWR)
        os.dup(fp)
        os.dup(fp)
        os.dup(fp)
    else:  # parent
        lock.setpid(pid)
        os.waitpid(pid, os.WNOHANG)
        sys.exit(0)


def setup_logging():
    """
    Set logging levels based on configuration.
    """
    cfg = AgentConfig()
    for name, level in cfg.logging:
        if not level:
            continue
        try:
            logger = logging.getLogger(name)
            level = getattr(logging, level.upper())
            logger.setLevel(level)
        except Exception, e:
            log.error(str(e))


def main():
    daemon = True
    setup_logging()
    try:
        opts, args = getopt(sys.argv[1:], 'hf:', ['help', 'foreground'])
        for opt,arg in opts:
            if opt in ('-h', '--help'):
                usage()
                sys.exit(0)
            if opt in ('-f', '--foreground'):
                daemon = False
                continue
        start(daemon)
    except GetoptError, e:
        print e
        usage()

if __name__ == '__main__':
    main()
