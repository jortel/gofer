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

import sys
import os
import logging
from getopt import getopt, GetoptError
from gofer import *
from gofer.agent import *
from gofer.agent.action import Actions
from gofer.agent.plugin import PluginLoader, Plugin
from gofer.agent.lock import Lock, LockFailed
from gofer.agent.config import Config, nvl
from gofer.agent.logutil import getLogger
from time import sleep
from threading import Thread

log = getLogger(__name__)
cfg = Config()


class ActionThread(Thread):
    """
    Run actions independantly of main thread.
    @ivar actions: A list of actions to run.
    @type actions: [L{Action},..]
    """
    
    def __init__(self, actions):
        """
        @param actions: A list of actions to run.
        @type actions: [L{Action},..]
        """
        self.actions = actions
        Thread.__init__(self, name='Actions')
        self.setDaemon(True)
   
    def run(self):
        """
        Run actions.
        """
        while True:
            for action in self.actions:
                action()
            sleep(1)


class PluginMonitorThread(Thread):
    """
    Run actions independantly of main thread.
    @ivar plugin: A plugin to monitor.
    @type plugin: L{Plugin}
    """

    def __init__(self, plugin):
        """
        @param plugin: A plugin to monitor.
        @type plugin: L{Plugin}
        """
        self.plugin = plugin
        self.lastuuid = None
        Thread.__init__(self, name='%s-monitor' % plugin.name)
        self.setDaemon(True)
   
    def run(self):
        """
        Monitor plugin attach/detach.
        """
        while True:
            self.update()
            sleep(1)
            
    def update(self):
        """
        Update plugin messaging sessions.
        v = (<uuid>,<ssn>)
        """
        plugin = self.plugin
        uuid = plugin.getuuid()
        if uuid == self.lastuuid:
            return # unchanged
        if plugin.detach():
            log.info('uuid="%s", detached', self.lastuuid)
        if not uuid:
            self.lastuuid = uuid
            return
        try:
            plugin.attach(uuid)
            log.info('uuid="%s", attached', uuid)
            self.lastuuid = uuid
        except:
            log.error('plugin %s', plugin.name, exc_info=1)
                    

class Agent:
    """
    Gofer (main) agent.
    Starts (2) threads.  A thread to run actions and
    another to monitor/update plugin sessions on the bus.
    """
    
    WAIT = None

    def __init__(self, plugins, actions):
        """
        @param plugins: A list of loaded plugins
        @type plugins: list
        @param actions: A list of loaded actions.
        @type actions: list
        """
        actionThread = ActionThread(actions)
        actionThread.start()
        for plugin in plugins:
            if not plugin.geturl():
                continue
            pt = PluginMonitorThread(plugin)
            pt.start()
        log.info('agent started.')
        actionThread.join(self.WAIT)


class AgentLock(Lock):
    """
    Agent lock ensure that agent only has single instance running.
    @cvar PATH: The lock file absolute path.
    @type PATH: str
    """

    PATH = '/var/run/%sd.pid' % NAME

    def __init__(self):
        Lock.__init__(self, self.PATH)


def start(daemon=True):
    """
    Agent main.
    Add recurring, time-based actions here.
    All actions must be subclass of L{action.Action}.
    """
    lock = AgentLock()
    try:
        lock.acquire(wait=False)
    except LockFailed, e:
        raise Exception('Agent already running')
    if daemon:
        daemonize(lock)
    try:
        pl = PluginLoader()
        plugins = pl.load()
        actions = Actions()
        collated = actions.collated()
        agent = Agent(plugins, collated)
    finally:
        lock.release()

def usage():
    """
    Show usage.
    """
    s = []
    s.append('\n%sd <options>' % NAME)
    s.append('  -h, --help')
    s.append('      Show help')
    s.append('  -c, --console')
    s.append('      Run in the foreground and not as a daemon.')
    s.append('      default: 0')
    s.append('  -p [seconds], --profile [seconds]')
    s.append('      Run (foreground) and print code profiling statistics.')
    s.append('\n')
    print '\n'.join(s)

def daemonize(lock):
    """
    Daemon configuration.
    """
    pid = os.fork()
    if pid == 0: # child
        os.setsid()
        os.chdir('/')
        os.close(0)
        os.close(1)
        os.close(2)
        dn = os.open('/dev/null', os.O_RDWR)
        os.dup(dn)
        os.dup(dn)
        os.dup(dn)
    else: # parent
        lock.update(pid)
        os.waitpid(pid, os.WNOHANG)
        os._exit(0)
        
def setupLogging():
    """
    Set logging levels based on configuration.
    """
    for p in nvl(cfg.logging, []):
        level = cfg.logging[p]
        if not level:
            continue
        try:
            name = 'gofer.%s' % p
            L = getattr(logging, level.upper())
            logger = logging.getLogger(name)
            logger.setLevel(L)
        except:
            pass
        
def profile(daemon=False):
    import pstats
    import cProfile
    fn='/tmp/gofer.pf'
    log.info('profile: %s', fn)
    cProfile.runctx(
        'start(0)',
        globals(),
        locals(),
        filename=fn)
    stats = pstats.Stats(fn)
    stats.strip_dirs()
    stats.sort_stats('cumulative')
    stats.print_stats()

def main():
    daemon = True
    __start = start
    setupLogging()
    try:
        opts, args = getopt(sys.argv[1:], 'hcp:', ['help','console','profile'])
        for opt,arg in opts:
            if opt in ('-h', '--help'):
                usage()
                sys.exit(0)
            if opt in ('-c', '--console'):
                daemon = False
                continue
            if opt in ('-p', '--profile'):
                __start = profile
                Agent.WAIT = int(arg)
                daemon = False
                continue
        __start(daemon)
    except GetoptError, e:
        print e
        usage()

if __name__ == '__main__':
    main()
