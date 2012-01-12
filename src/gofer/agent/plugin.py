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
import inspect
from threading import RLock
from gofer import *
from gofer.rmi.dispatcher import Dispatcher
from gofer.rmi.threadpool import Immediate, ThreadPool
from gofer.rmi.consumer import RequestConsumer
from gofer.rmi.decorators import Remote
from gofer.agent.deplist import DepList
from gofer.agent.config import Base, Config, nvl
from gofer.agent.action import Actions
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
        self.impl = None
        self.actions = []
        self.dispatcher = Dispatcher([])
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
            
    def seturl(self, url, save=False):
        """
        Set the plugin's URL.
        @param url: The new URL.
        @type url: str
        @param save: Save to plugin descriptor.
        @type save: bool
        """
        self.__lock()
        try:
            cfg = self.cfg()
            if url:
                cfg.messaging.url = url
            else:
                delattr(cfg.messaging, 'url')
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
        """
        Get the plugin descriptor.
        @return: The plugin descriptor
        @rtype: L{Config}
        """
        return self.descriptor
    
    def dispatch(self, request):
        """
        Dispatch (invoke) the specified RMI request.
        @param request: An RMI request
        @type request: L{Envelope}
        @return: The RMI returned.
        """
        return self.dispatcher.dispatch(request)
    
    def provides(self, name):
        """
        Get whether a plugin provides the specified class.
        @param name: A class (or module) name.
        @type name: str
        @return: True if provides.
        @rtype: bool
        """
        return self.dispatcher.provides(name)
    
    def export(self, name):
        """
        Export an object defined in the plugin (module).
        The name must reference a class or function object.
        @param name: A name (class|function)
        @type name: str
        @return: The named item.
        @rtype: (class|function)
        @raise NameError: when not found
        """
        try:
            obj = getattr(self.impl, name)
            valid = inspect.isclass(obj) or inspect.isfunction(obj)
            if valid:
                return obj
            raise TypeError, '(%s) must be class|function' % name
        except AttributeError:
            raise NameError(name)
    
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
        unsorted = []
        cls.__mkdir()
        for name, path in cls.__list():
            try:
                inst = cls(path)
                inst.__dict__['__path__'] = path
                unsorted.append((name, inst))
            except:
                log.exception(path)
        return cls.__sort(unsorted)
    
    @classmethod
    def __list(cls):
        files = os.listdir(cls.ROOT)
        for fn in sorted(files):
            plugin,ext = fn.split('.',1)
            if not ext in ('.conf'):
                continue
            path = os.path.join(cls.ROOT, fn)
            if os.path.isdir(path):
                continue
            yield (plugin, path)
    
    @classmethod
    def __sort(cls, descriptors):
        """
        Sort descriptors based on defined dependencies.
        Dependencies defined by [main].requires
        @param descriptors: A list of descriptor tuples (name,descriptor)
        @type descriptors: list
        @return: The sorted list
        @rtype: list
        """
        index = {}
        for d in descriptors:
            index[d[0]] = d
        L = DepList()
        for n,d in descriptors:
            r = (n, d.__requires())
            L.add(r)
        sorted = []
        for name in [x[0] for x in L.sort()]:
            d = index[name]
            sorted.append(d)
        return sorted

    def __requires(self):
        """
        Get the list of declared required plugins.
        @return: A list of plugin names.
        @rtype: list
        """
        required = []
        declared = nvl(self.main.requires)
        if declared:
            plugins =  declared.split(',')
            required = [s.strip() for s in plugins]
        return tuple(required)
    
    def write(self):
        """
        Write the descriptor to the filesystem
        Written to: __path__.
        """
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

    def load(self, eager=True):
        """
        Load the plugins.
        @param eager: Load disabled plugins.
        @type eager: bool
        @return: A list of loaded plugins
        @rtype: list
        """
        loaded = []
        for plugin, cfg in PluginDescriptor.load():
            if self.__noload(cfg, eager):
                continue
            p = self.__import(plugin, cfg)
            if not p:
                continue # load failed
            if not p.enabled():
                log.warn('plugin: %s, DISABLED', p.name)
            loaded.append(p)
        return loaded
    
    def __noload(self, cfg, eager):
        """
        Determine whether the plugin should be loaded.
        @param cfg: A plugin descriptor.
        @type cfg: L{PluginDescriptor}
        @param eager: The I{eager} load flag.
        @type eager: bool
        @return: True when not loaded.
        @rtype: bool
        """
        try:
            return not ( eager or int(cfg.main.enabled) )
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
        Actions.clear()
        syn = self.__mangled(plugin)
        p = Plugin(plugin, cfg, (syn,))
        Plugin.add(p)
        try:
            path = self.__findplugin(plugin)
            mod = imp.load_source(syn, path)
            p.impl = mod
            log.info('plugin "%s", imported as: "%s"', plugin, syn)
            for fn in Remote.find(syn):
                fn.gofer.plugin = p
            if p.enabled():
                collated = Remote.collated()
                p.dispatcher = Dispatcher(collated)
                p.actions = Actions.collated()
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
        raise Exception('%s, not found in:%s' % (mod, self.PATH))
        
            
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
