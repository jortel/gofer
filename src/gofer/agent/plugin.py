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
Plugin classes.
"""

import os
import sys
import imp
from threading import RLock
from gofer import *
from gofer.rmi.dispatcher import Dispatcher
from gofer.rmi.threadpool import Immediate, ThreadPool
from gofer.rmi.consumer import RequestConsumer
from gofer.rmi.decorators import Remote
from gofer.agent.config import Base, Config, nvl
from gofer.messaging import Queue
from gofer.messaging.broker import Broker
from logging import getLogger

log = getLogger(__name__)


class Plugin(object):
    """
    Represents a plugin.
    @ivar name: The plugin name.
    @type name: str
    @ivar synonyms: The plugin synonyms.
    @type synonyms: list
    @ivar descriptor: The plugin descriptor.
    @type descriptor: str
    @cvar plugins: The dict of loaded plugins.
    @type plugins: dict
    """
    plugins = {}
    
    @classmethod
    def add(cls, plugin):
        """
        Add the plugin.
        @param plugin: The plugin to add.
        @type plugin: L{Plugin}
        @return: The added plugin
        @rtype: L{Plugin}
        """
        cls.plugins[plugin.name] = plugin
        for syn in plugin.synonyms:
            if syn == plugin.name:
                continue
            cls.plugins[syn] = plugin
        return plugin
    
    @classmethod
    def delete(cls, plugin):
        """
        Delete the plugin.
        @param plugin: The plugin to delete.
        @type plugin: L{Plugin}
        """
        for k,v in cls.plugins.items():
            if v == plugin:
                del cls.plugins[k]
        return plugin
    
    @classmethod
    def find(cls, name):
        """
        Find a plugin by name or synonym.
        @param name: A plugin name or synonym.
        @type name: str
        @return: The plugin when found.
        @rtype: L{Plugin} 
        """
        return cls.plugins.get(name)
    
    @classmethod
    def all(cls):
        """
        Get a unique list of loaded plugins.
        @return: A list of plugins
        @rtype: list
        """
        unique = []
        for p in cls.plugins.values():
            if p in unique:
                continue
            unique.append(p)
        return unique
    
    def __init__(self, name, descriptor, synonyms=[]):
        """
        @param name: The plugin name.
        @type name: str
        @param descriptor: The plugin descriptor.
        @type descriptor: str
        @param synonyms: The plugin synonyms.
        @type synonyms: list
        """
        self.name = name
        self.descriptor = descriptor
        self.synonyms = []
        for syn in synonyms:
            if syn == name:
                continue
            self.synonyms.append(syn)
        self.__mutex = RLock()
        self.__pool = None
        self.dispatcher = None
        self.consumer = None
        
    def names(self):
        """
        Get I{all} the names by which the plugin can be found.
        @return: A list of name and synonyms.
        @rtype: list
        """
        names = [self.name]
        names += self.synonyms
        return names
    
    def enabled(self):
        """
        Get whether the plugin is enabled.
        @return: True if enabled.
        @rtype: bool
        """
        cfg = self.cfg()
        try:
            return int(nvl(cfg.main.enabled, 0))
        except:
            return 0
        
    def getuuid(self):
        """
        Get the plugin's messaging UUID.
        @return: The plugin's messaging UUID.
        @rtype: str
        """
        self.__lock()
        try:
            cfg = self.cfg()
            return nvl(cfg.messaging.uuid)
        finally:
            self.__unlock()
            
    def geturl(self):
        """
        Get the broker URL
        @return: The broker URL
        @rtype: str
        """
        main = Config()
        cfg = self.cfg()
        return nvl(cfg.messaging.url,
               nvl(main.messaging.url))
    
    def getbroker(self):
        """
        Get the amqp broker for this plugin.  Each plugin can
        connect to a different broker.
        @return: The broker if configured.
        @rtype: L{Broker}
        """
        cfg = self.cfg()
        main = Config()
        broker = Broker(self.geturl())
        broker.cacert = \
            nvl(cfg.messaging.cacert,
            nvl(main.messaging.cacert))
        broker.clientcert = \
            nvl(cfg.messaging.clientcert,
            nvl(main.messaging.clientcert))
        log.info('broker (qpid) configured: %s', broker)
        return broker
    
    def getpool(self):
        """
        Get the plugin's thread pool.
        @return: ThreadPool.
        """
        if self.__pool is None:
            n = self.nthreads()
            self.__pool = ThreadPool(1, n)
        return self.__pool
    
    def setuuid(self, uuid, save=False):
        """
        Set the plugin's UUID.
        @param uuid: The new UUID.
        @type uuid: str
        @param save: Save to plugin descriptor.
        @type save: bool
        """
        self.__lock()
        try:
            cfg = self.cfg()
            if uuid:
                cfg.messaging.uuid = uuid
            else:
                delattr(cfg.messaging, 'uuid')
            if save:
                cfg.write()
        finally:
            self.__unlock()
            
    def nthreads(self):
        """
        Get the number of theads in the plugin's pool.
        @return: number of theads.
        @rtype: int
        """
        main = Config()
        cfg = self.cfg()
        value = \
            nvl(cfg.messaging.threads,
            nvl(main.messaging.threads, 1))
        value = int(value)
        assert(value >= 1)
        return value

    def attach(self, uuid=None):
        """
        Attach (connect) to AMQP broker using the specified uuid.
        @param uuid: The (optional) messaging UUID.
        @type uuid: str
        """
        cfg = self.cfg()
        if not uuid:
            uuid = self.getuuid()
        broker = self.getbroker()
        url = broker.url
        queue = Queue(uuid)
        consumer = RequestConsumer(queue, url=url)
        consumer.start()
        self.consumer = consumer
    
    def detach(self):
        """
        Detach (disconnect) from AMQP broker (if connected).
        """
        if self.consumer:
            self.consumer.close()
            self.consumer = None
            return True
        else:
            return False
        
    def cfg(self):
        return self.descriptor
    
    def dispatch(self, request):
        return self.dispatcher.dispatch(request)
    
    def provides(self, classname):
        return self.dispatcher.provides(classname)
    
    def __lock(self):
        self.__mutex.acquire()
        
    def __unlock(self):
        self.__mutex.release()


class PluginDescriptor(Base):
    """
    Provides a plugin descriptor
    """
    
    ROOT = '/etc/%s/plugins' % NAME
    
    @classmethod
    def __mkdir(cls):
        if not os.path.exists(cls.ROOT):
            os.makedirs(cls.ROOT)
    
    @classmethod
    def load(cls):
        """
        Load the plugin descriptors.
        @return: A list of descriptors.
        @rtype: list
        """
        lst = []
        cls.__mkdir()
        for fn in os.listdir(cls.ROOT):
            plugin,ext = fn.split('.',1)
            if not ext in ('.conf'):
                continue
            path = os.path.join(cls.ROOT, fn)
            if os.path.isdir(path):
                continue
            try:
                inst = cls(path)
                inst.__dict__['__path__'] = path
                lst.append((plugin, inst))
            except:
                log.error(path, exc_info=1)
        return lst
    
    def write(self):
        path = self.__dict__['__path__']
        f = open(path, 'w')
        f.write(str(self))
        f.close()


class PluginLoader:
    """
    Agent plugins loader.
    @ivar plugins: A dict of plugins and configuratons
    @type plugins: dict
    """

    PATH = [
        '/usr/lib/%s/plugins' % NAME,
        '/usr/lib64/%s/plugins' % NAME,
        '/opt/%s/plugins' % NAME,
    ]

    def load(self):
        """
        Load the plugins.
        @return: A list of loaded plugins
        @rtype: list
        """
        loaded = []
        for plugin, cfg in PluginDescriptor.load():
            enabled = self.__enabled(cfg)
            if not enabled:
                continue
            p = self.__import(plugin, cfg)
            if not p:
                continue
            loaded.append(p)
        return loaded
                
    def __enabled(self, cfg):
        """
        Safely validate the plugin is enabled.
        @param cfg: A plugin descriptor.
        @type cfg: L{PluginDescriptor}
        @return: True if enabled.
        @rtype: bool
        """
        try:
            return int(cfg.main.enabled)
        except:
            return False

    def __import(self, plugin, cfg):
        """
        Import a module by file name.
        @param plugin: The plugin (module) name.
        @type plugin: str
        @param cfg: A plugin descriptor.
        @type cfg: L{PluginDescriptor}
        @return: The loaded module.
        @rtype: Module
        """
        Remote.clear()
        syn = self.__mangled(plugin)
        p = Plugin(plugin, cfg, (syn,))
        Plugin.add(p)
        try:
            path = self.__findplugin(plugin)
            mod = imp.load_source(syn, path)
            log.info('plugin "%s", imported as: "%s"', plugin, syn)
            for fn in Remote.find(syn):
                fn.gofer.plugin = p
            collated = Remote.collated()
            p.dispatcher = Dispatcher(collated)
            return p
        except:
            Plugin.delete(p)
            log.exception('plugin "%s", import failed', plugin)
            
    def __findplugin(self, plugin):
        """
        Find a plugin module.
        @param plugin: The plugin name.
        @type plugin: str
        @return: The fully qualified path to the plugin module.
        @rtype: str
        @raise Exception: When not found.
        """
        mod = '%s.py' % plugin
        for root in self.PATH:
            path = os.path.join(root, mod)
            if os.path.exists(path):
                log.info('using: %s', path)
                return path
        raise Exception('%s, not found in:%s', mod, self.PATH)
        
            
    def __mangled(self, plugin):
        """
        Get the module name for the specified plugin.
        @param plugin: The name of the plugin.
        @type plugin: str
        @return: The (mangled if necessary) plugin's module name.
        @rtype: str
        """
        try:
            imp.find_module(plugin)
            log.warn('"%s" found in python-path', plugin)
            log.info('"%s" mangled to avoid collisions', plugin)
            return '%s_plugin' % plugin
        except:
            return plugin
