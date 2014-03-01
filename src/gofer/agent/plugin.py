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
import imp
import errno

from logging import getLogger

from gofer import *
from gofer.rmi.dispatcher import Dispatcher
from gofer.rmi.threadpool import ThreadPool
from gofer.rmi.consumer import RequestConsumer
from gofer.rmi.decorators import Remote
from gofer.agent.deplist import DepList
from gofer.agent.config import AgentConfig
from gofer.config import Config, Graph, get_bool
from gofer.agent.action import Actions
from gofer.agent.whiteboard import Whiteboard
from gofer.transport import Transport


log = getLogger(__name__)


class Plugin(object):
    """
    Represents a plugin.
    :ivar name: The plugin name.
    :type name: str
    :ivar synonyms: The plugin synonyms.
    :type synonyms: list
    :ivar descriptor: The plugin descriptor.
    :type descriptor: PluginDescriptor
    :cvar plugins: The dict of loaded plugins.
    :type plugins: dict
    """
    plugins = {}
    
    @classmethod
    def add(cls, plugin):
        """
        Add the plugin.
        :param plugin: The plugin to add.
        :type plugin: Plugin
        :return: The added plugin
        :rtype: Plugin
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
        :param plugin: The plugin to delete.
        :type plugin: Plugin
        """
        for k,v in cls.plugins.items():
            if v == plugin:
                del cls.plugins[k]
        return plugin
    
    @classmethod
    def find(cls, name):
        """
        Find a plugin by name or synonym.
        :param name: A plugin name or synonym.
        :type name: str
        :return: The plugin when found.
        :rtype: Plugin 
        """
        return cls.plugins.get(name)
    
    @classmethod
    def all(cls):
        """
        Get a unique list of loaded plugins.
        :return: A list of plugins
        :rtype: list
        """
        unique = []
        for p in cls.plugins.values():
            if p in unique:
                continue
            unique.append(p)
        return unique
    
    def __init__(self, name, descriptor, synonyms=None):
        """
        :param name: The plugin name.
        :type name: str
        :param descriptor: The plugin descriptor.
        :type descriptor: PluginDescriptor
        :param synonyms: The plugin synonyms.
        :type synonyms: list
        """
        self.name = name
        self.descriptor = descriptor
        self.synonyms = []
        for syn in synonyms or []:
            if syn == name:
                continue
            self.synonyms.append(syn)
        self.pool = ThreadPool(int(descriptor.messaging.threads or 1))
        self.impl = None
        self.actions = []
        self.dispatcher = Dispatcher([])
        self.whiteboard = Whiteboard()
        self.authenticator = None
        self.consumer = None
        
    def names(self):
        """
        Get I{all} the names by which the plugin can be found.
        :return: A list of name and synonyms.
        :rtype: list
        """
        names = [self.name]
        names += self.synonyms
        return names
    
    def enabled(self):
        """
        Get whether the plugin is enabled.
        :return: True if enabled.
        :rtype: bool
        """
        return get_bool(self.descriptor.main.enabled)
        
    def get_uuid(self):
        """
        Get the plugin's messaging UUID.
        :return: The plugin's messaging UUID.
        :rtype: str
        """
        return self.descriptor.messaging.uuid
            
    def get_url(self):
        """
        Get the broker URL
        :return: The broker URL
        :rtype: str
        """
        agent = AgentConfig()
        plugin = self.descriptor
        return plugin.messaging.url or agent.messaging.url
    
    def get_broker(self):
        """
        Get the amqp broker for this plugin.
        Each plugin can connect to a different broker.
        :return: The broker if configured.
        :rtype: gofer.transport.broker.Broker
        """
        agent = AgentConfig()
        plugin = self.descriptor
        url = self.get_url()
        transport = self.get_transport()
        broker = transport.broker(url)
        broker.cacert = plugin.messaging.cacert or agent.messaging.cacert
        broker.clientcert = plugin.messaging.clientcert or agent.messaging.clientcert
        broker.validation = get_bool(plugin.messaging.validation or agent.messaging.validation)
        log.debug('broker (qpid) configured: %s', broker)
        return broker
    
    def set_uuid(self, uuid):
        """
        Set the plugin's UUID.
        :param uuid: The new UUID.
        :type uuid: str
        """
        self.descriptor.messaging.uuid = uuid
            
    def set_url(self, url):
        """
        Set the plugin's URL.
        :param url: The new URL.
        :type url: str
        """
        self.descriptor.messaging.url = url

    def get_transport(self):
        """
        Get the AMQP transport for the plugin.
        :return: The transport.
        :rtype: Transport
        """
        agent = AgentConfig()
        plugin = self.descriptor
        package = plugin.messaging.transport or agent.messaging.transport
        return Transport(package)

    def set_transport(self, transport):
        """
        Set the plugin's transport package (name).
        :param transport: The new transport package.
        :type transport: str
        """
        self.descriptor.messaging.transport = transport

    def attach(self, uuid=None):
        """
        Attach (connect) to AMQP broker using the specified uuid.
        :param uuid: The (optional) messaging UUID.
        :type uuid: str
        """
        if not uuid:
            uuid = self.get_uuid()
        url = self.get_url()
        tp = self.get_transport()
        queue = tp.queue(uuid)
        consumer = RequestConsumer(queue, url=url, transport=tp)
        consumer.reader.authenticator = self.authenticator
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
        :return: The plugin descriptor
        :rtype: PluginDescriptor
        """
        return self.descriptor
    
    def dispatch(self, request):
        """
        Dispatch (invoke) the specified RMI request.
        :param request: An RMI request
        :type request: Document
        :return: The RMI returned.
        """
        return self.dispatcher.dispatch(request)
    
    def provides(self, name):
        """
        Get whether a plugin provides the specified class.
        :param name: A class (or module) name.
        :type name: str
        :return: True if provides.
        :rtype: bool
        """
        return self.dispatcher.provides(name)
    
    def export(self, name):
        """
        Export an object defined in the plugin (module).
        The name must reference a class or function object.
        :param name: A name (class|function)
        :type name: str
        :return: The named item.
        :rtype: (class|function)
        :raise NameError: when not found
        """
        try:
            obj = getattr(self.impl, name)
            valid = inspect.isclass(obj) or inspect.isfunction(obj)
            if valid:
                return obj
            raise TypeError('(%s) must be class|function' % name)
        except AttributeError:
            raise NameError(name)

    # deprecated
    getuuid = get_uuid
    geturl = get_url
    getbroker = get_broker
    setuuid = set_uuid
    seturl = set_url


class PluginDescriptor(Graph):
    """
    Provides a plugin descriptor
    """
    
    ROOT = '/etc/%s/plugins' % NAME
    
    @staticmethod
    def __mkdir():
        try:
            os.makedirs(PluginDescriptor.ROOT)
        except OSError, e:
            if e.errno != errno.EEXIST:
                raise
    
    @staticmethod
    def load():
        """
        Load the plugin descriptors.
        :return: A list of descriptors.
        :rtype: list
        """
        unsorted = []
        PluginDescriptor.__mkdir()
        for name, path in PluginDescriptor.__list():
            try:
                conf = Config(path)
                inst = PluginDescriptor(conf)
                unsorted.append((name, inst))
            except Exception:
                log.exception(path)
        return PluginDescriptor.__sort(unsorted)
    
    @staticmethod
    def __list():
        files = os.listdir(PluginDescriptor.ROOT)
        for fn in sorted(files):
            plugin, ext = fn.split('.', 1)
            if not ext in ('conf',):
                continue
            path = os.path.join(PluginDescriptor.ROOT, fn)
            if os.path.isdir(path):
                continue
            yield (plugin, path)
    
    @staticmethod
    def __sort(descriptors):
        """
        Sort descriptors based on defined dependencies.
        Dependencies defined by [main].requires
        :param descriptors: A list of descriptor tuples (name,descriptor)
        :type descriptors: list
        :return: The sorted list
        :rtype: list
        """
        index = {}
        for d in descriptors:
            index[d[0]] = d
        dl = DepList()
        for n, d in descriptors:
            r = (n, d.__requires())
            dl.add(r)
        _sorted = []
        for name in [x[0] for x in dl.sort()]:
            d = index[name]
            _sorted.append(d)
        return _sorted

    def __requires(self):
        """
        Get the list of declared required plugins.
        :return: A list of plugin names.
        :rtype: list
        """
        required = []
        declared = self.main.requires
        if declared:
            plugins = declared.split(',')
            required = [s.strip() for s in plugins]
        return tuple(required)


class PluginLoader:
    """
    Agent plugins loader.
    :cvar PATH: A list of paths to directories containing plugins.
    :type PATH: list
    """

    PATH = [
        '/usr/share/%s/plugins' % NAME,
        '/usr/lib/%s/plugins' % NAME,
        '/usr/lib64/%s/plugins' % NAME,
        '/opt/%s/plugins' % NAME,
    ]

    BUILTIN = __import__('gofer.agent.builtin')
    BUILTINS = Remote.collated()

    @staticmethod
    def find_plugin(plugin):
        """
        Find a plugin module.
        :param plugin: The plugin name.
        :type plugin: str
        :return: The fully qualified path to the plugin module.
        :rtype: str
        :raise Exception: When not found.
        """
        mod = '%s.py' % plugin
        for root in PluginLoader.PATH:
            path = os.path.join(root, mod)
            if os.path.exists(path):
                log.info('using: %s', path)
                return path
        raise Exception('%s, not found in:%s' % (mod, PluginLoader.PATH))

    @staticmethod
    def mangled(plugin):
        """
        Get the module name for the specified plugin.
        :param plugin: The name of the plugin.
        :type plugin: str
        :return: The (mangled if necessary) plugin's module name.
        :rtype: str
        """
        try:
            imp.find_module(plugin)
            log.warn('"%s" found in python-path', plugin)
            log.info('"%s" mangled to avoid collisions', plugin)
            return '%s_plugin' % plugin
        except Exception:
            return plugin

    @staticmethod
    def load(eager=True):
        """
        Load the plugins.
        :param eager: Load disabled plugins.
        :type eager: bool
        :return: A list of loaded plugins
        :rtype: list
        """
        loaded = []
        for plugin, descriptor in PluginDescriptor.load():
            if PluginLoader.no_load(descriptor, eager):
                continue
            p = PluginLoader._import(plugin, descriptor)
            if not p:
                continue  # load failed
            if not p.enabled():
                log.warn('plugin: %s, DISABLED', p.name)
            loaded.append(p)
        return loaded

    @staticmethod
    def no_load(descriptor, eager):
        """
        Determine whether the plugin should be loaded.
        :param descriptor: A plugin descriptor.
        :type descriptor: PluginDescriptor
        :param eager: The I{eager} load flag.
        :type eager: bool
        :return: True when not loaded.
        :rtype: bool
        """
        try:
            return not (eager or get_bool(descriptor.main.enabled))
        except Exception:
            return False

    @staticmethod
    def _import(plugin, descriptor):
        """
        Import a module by file name.
        :param plugin: The plugin (module) name.
        :type plugin: str
        :param descriptor: A plugin descriptor.
        :type descriptor: PluginDescriptor
        :return: The loaded module.
        :rtype: Plugin
        """
        Remote.clear()
        Actions.clear()
        syn = PluginLoader.mangled(plugin)
        p = Plugin(plugin, descriptor, [syn])
        Plugin.add(p)
        try:
            path = PluginLoader.find_plugin(plugin)
            mod = imp.load_source(syn, path)
            p.impl = mod
            log.info('plugin "%s", imported as: "%s"', plugin, syn)
            for fn in Remote.find(syn):
                fn.gofer.plugin = p
            if p.enabled():
                collated = Remote.collated()
                collated += PluginLoader.BUILTINS
                p.dispatcher = Dispatcher(collated)
                p.actions = Actions.collated()
            return p
        except Exception:
            Plugin.delete(p)
            log.exception('plugin "%s", import failed', plugin)
