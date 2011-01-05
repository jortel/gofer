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
from getopt import getopt
from gofer import *
from gofer.agent import *
from gofer.agent.action import Actions
from gofer.agent.plugin import PluginLoader, Plugin
from gofer.agent.lock import Lock, LockFailed
from gofer.agent.config import Config, nvl
from gofer.agent.logutil import getLogger
from gofer.messaging import Queue
from gofer.messaging.broker import Broker
from gofer.messaging.base import Agent as Session
from gofer.messaging.consumer import RequestConsumer
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
    @ivar plugins: A list of plugins to load.
    @type plugins: [L{Plugin},..]
    """
    
    URL = 'tcp://localhost:5672'
    
    def __init__(self, plugins):
        """
        @param plugins: A list of plugins to monitor.
        @type plugins: [L{Plugin},..]
        """
        self.plugins = {}
        for p in plugins:
            self.plugins[p] = None
        Thread.__init__(self, name='PluginMonitor')
        self.setDaemon(True)
   
    def run(self):
        """
        Monitor plugin attach/detach.
        """
        self.setupBroker()
        while True:
            self.update()
            sleep(1)
            
    def update(self):
        """
        Update plugin messaging sessions.
        v = (<uuid>,<ssn>)
        """
        for plugin,v in self.plugins.items():
            if not v:
                v = [None, None]
                self.plugins[plugin] = v
            uuid = plugin.getuuid()
            if v[0] == uuid:
                continue # unchanged
            ssn = v[1]
            if ssn:
                ssn.close()
                log.info('messaging stopped for uuid="%s"', v[0])
            if not uuid:
                v[0] = None
                continue
            try:
                v[0] = uuid
                v[1] = self.attach(plugin, uuid)
            except:
                log.error('plugin %s', plugin.name, exc_info=1)
                    
    def attach(self, plugin, uuid):
        """
        Start an AMQP session (attach).
        @param plugin: A plugin.
        @type plugin: L{Plugin}
        @param uuid: A messaging consumer uuid.
        @type uuid: str
        @return: A new session.
        @rtype: L{Session}
        """
        pd = plugin.cfg()
        if not self.enabled(pd):
            return
        url = self.url()
        queue = Queue(uuid)
        consumer = RequestConsumer(queue, url=url)
        ssn = Session(consumer)
        log.info('messaging started for uuid="%s".', uuid)
        return ssn
    
    def enabled(self, pd):
        """
        Get whether messaging is enabled.
        @param pd: A plugin descriptor.
        @type pd: L{PluginDescriptor}
        @return: True if enabled.
        @rtype: bool
        """
        try:
            return int(pd.messaging.enabled)
        except:
            return 0
        
    def url(self):
        """
        Get the messaging url.
        @return: Either the url specified in the conf or the default.
        @rtype: str
        """
        try:
            return cfg.messaging.url
        except:
            return self.URL
    
    def setupBroker(self):
        """
        Setup (configure) the broker using the conf.
        @return: self
        @rtype: L{PluginMonitorThread}
        """
        url = self.url()
        broker = Broker.get(url)
        for property in ('cacert', 'clientcert'):
            try:
                v = getattr(cfg.messaging, property)
                setattr(broker, property, v)
            except AttributeError:
                pass
        log.info('broker (qpid) configured: %s', broker)
        return self


class Agent:
    """
    Gofer (main) agent.
    Starts (2) threads.  A thread to run actions and
    another to monitor/update plugin sessions on the bus.
    """

    def __init__(self, plugins, actions):
        """
        @param plugins: A list of loaded plugins
        @type plugins: list
        @param actions: A list of loaded actions.
        @type actions: list
        """
        self.plugins = {}
        for p in plugins:
            self.plugins[p] = (None, None)
        actionThread = ActionThread(actions)
        actionThread.start()
        pluginThread = PluginMonitorThread(plugins)
        pluginThread.start()
        log.info('agent started.')
        actionThread.join()


class AgentLock(Lock):
    """
    Agent lock ensure that agent only has single instance running.
    @cvar PATH: The lock file absolute path.
    @type PATH: str
    """

    PATH = '/var/run/goferd.pid'

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
        agent.close()
    finally:
        lock.release()

def usage():
    """
    Show usage.
    """
    s = []
    s.append('\ngoferd <optoins>')
    s.append('  -h, --help')
    s.append('      Show help')
    s.append('  -c, --console')
    s.append('      Run in the foreground and not as a daemon.')
    s.append('      default: 0')
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

def main():
    daemon = True
    setupLogging()
    opts, args = getopt(sys.argv[1:], 'hc', ['help','console'])
    for opt,arg in opts:
        if opt in ('-h', '--help'):
            usage()
            sys.exit(0)
        if opt in ('-c', '--console'):
            daemon = False
            continue
    start(daemon)

if __name__ == '__main__':
    main()
