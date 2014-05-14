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
from gofer.collator import Module


log = getLogger(__name__)


class Initializer(object):
    """
    Plugin initializer collection.
    :cvar initializer: List of initializer functions.
    :type initializer: list
    """

    initializer = []

    @staticmethod
    def add(function):
        """
        Add an initializer.
        :param function: The function to add.
        :type function: function
        """
        Initializer.initializer.append(function)

    @staticmethod
    def clear():
        """
        Clear the initializer list.
        """
        Initializer.initializer = []

    @staticmethod
    def run():
        """
        Run initializer functions.
        """
        for function in Initializer.initializer:
            function()


def initializer(fn):
    """
    Plugin @initializer decorator.
    :param fn: A plugin initializer function.
    :type fn: function
    :return: fn
    :rtype: function
    """
    Initializer.add(fn)
    return fn


class Plugin(object):
    """
    Represents a plugin.
    :ivar name: The plugin name.
    :type name: str
    :ivar descriptor: The plugin descriptor.
    :type descriptor: PluginDescriptor
    :cvar plugins: The dict of loaded plugins.
    :type plugins: dict
    """
    plugins = {}
    
    @staticmethod
    def add(plugin, *names):
        """
        Add the plugin.
        :param plugin: The plugin to add.
        :type plugin: Plugin
        :return: The added plugin
        :rtype: Plugin
        """
        if not names:
            names = (plugin.name,)
        for name in names:
            Plugin.plugins[name] = plugin
        return plugin
    
    @staticmethod
    def delete(plugin):
        """
        Delete the plugin.
        :param plugin: The plugin to delete.
        :type plugin: Plugin
        """
        for k, v in Plugin.plugins.items():
            if v == plugin:
                del Plugin.plugins[k]
        return plugin
    
    @staticmethod
    def find(name):
        """
        Find a plugin by name
        :param name: A plugin name
        :type name: str
        :return: The plugin when found.
        :rtype: Plugin 
        """
        return Plugin.plugins.get(name)
    
    @staticmethod
    def all():
        """
        Get a unique list of loaded plugins.
        :return: A list of plugins
        :rtype: list
        """
        unique = []
        for p in Plugin.plugins.values():
            if p in unique:
                continue
            unique.append(p)
        return unique

    def __init__(self, name, descriptor):
        """
        :param name: The plugin name.
        :type name: str
        :param descriptor: The plugin descriptor.
        :type descriptor: PluginDescriptor
        """
        self.name = name
        self.descriptor = descriptor
        self.pool = ThreadPool(int(descriptor.messaging.threads or 1))
        self.impl = None
        self.actions = []
        self.dispatcher = Dispatcher()
        self.whiteboard = Whiteboard()
        self.authenticator = None
        self.consumer = None
        self.imported = {}
    
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
        Get the broker for this plugin.
        :return: The configured broker.
        :rtype: gofer.transport.broker.Broker
        """
        return self.update_broker()

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
        :rtype: str
        """
        agent = AgentConfig()
        plugin = self.descriptor
        return plugin.messaging.transport or agent.messaging.transport

    def update_broker(self):
        """
        Update the broker configuration using the plugin configuration.
        :return: The updated broker.
        :rtype: gofer.transport.broker.Broker
        """
        agent = AgentConfig()
        plugin = self.descriptor
        url = self.get_url()
        tp = Transport(self.get_transport())
        broker = tp.broker(url)
        broker.virtual_host = \
            plugin.messaging.virtual_host or agent.messaging.virtual_host
        broker.userid = \
            plugin.messaging.userid or agent.messaging.userid
        broker.password = \
            plugin.messaging.password or agent.messaging.password
        broker.cacert = \
            plugin.messaging.cacert or agent.messaging.cacert
        broker.clientcert = \
            plugin.messaging.clientcert or agent.messaging.clientcert
        broker.host_validation = \
            get_bool(plugin.messaging.host_validation or agent.messaging.host_validation)
        log.debug('broker (qpid) configured: %s', broker)
        return broker

    def attach(self, uuid=None):
        """
        Attach (connect) to AMQP broker using the specified uuid.
        :param uuid: The (optional) messaging UUID.
        :type uuid: str
        """
        self.detach()
        if not uuid:
            uuid = self.get_uuid()
        url = self.get_url()
        transport = self.get_transport()
        if uuid and url:
            self.update_broker()
            tp = Transport(transport)
            queue = tp.queue(uuid)
            consumer = RequestConsumer(queue, url=url, transport=transport)
            consumer.reader.authenticator = self.authenticator
            consumer.start()
            log.info('plugin uuid="%s", attached', uuid)
            self.consumer = consumer
        else:
            log.error('plugin attach requires uuid and url')

    def detach(self):
        """
        Detach (disconnect) from AMQP broker.
        """
        if not self.consumer:
            return
        self.consumer.stop()
        self.consumer.join()
        self.consumer = None
        log.info('plugin uuid="%s", detached', self.get_uuid())
        
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

    def extend(self):
        """
        Find and extend the plugin defined by the descriptor.
        :return: The extended plugin.
        :rtype: Plugin
        """
        name = self.descriptor.main.extends
        if not name:
            # nothing specified
            return
        extended = Plugin.find(name.strip())
        if not extended:
            raise Exception('Extension failed. plugin: %s, not-found')
        extended += self
        return extended

    # deprecated
    getuuid = get_uuid
    geturl = get_url
    getbroker = get_broker
    setuuid = set_uuid
    seturl = set_url

    def __getitem__(self, key):
        try:
            return self.dispatcher[key]
        except KeyError:
            return self.dispatcher[self.name][key]

    def __iter__(self):
        return iter(self.dispatcher)

    def __iadd__(self, other):
        if isinstance(other, Plugin):
            for thing in other:
                self.__iadd__(thing)
            return self
        if inspect.isclass(other):
            self.dispatcher[other.__name__] = other
            return self
        if inspect.isfunction(other):
            try:
                mod = self.dispatcher[self.name]
            except KeyError:
                mod = Module(self.name)
                self.dispatcher[self.name] = mod
            mod += other
            return self
        return self


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
                descriptor = PluginDescriptor(Config(path))
                unsorted.append((descriptor.main.name or name, descriptor))
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
        required = set()
        declared = self.main.requires
        if declared:
            plugins = declared.split(',')
            required.update([s.strip() for s in plugins])
        extends = self.main.extends
        if extends:
            required.add(extends.strip())
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
                return path
        raise Exception('%s, not found in:%s' % (mod, PluginLoader.PATH))

    @staticmethod
    def load():
        """
        Load the plugins.
        :return: A list of loaded plugins
        :rtype: list
        """
        loaded = []
        for name, descriptor in PluginDescriptor.load():
            if not get_bool(descriptor.main.enabled):
                continue
            plugin = PluginLoader._import(name, descriptor)
            if not plugin:
                continue  # load failed
            if not plugin.enabled():
                log.warn('plugin: %s, DISABLED', name)
            loaded.append(plugin)
        return loaded

    @staticmethod
    def _import(name, descriptor):
        """
        Import a module by file name.
        :param name: The plugin (module) name.
        :type name: str
        :param descriptor: A plugin descriptor.
        :type descriptor: PluginDescriptor
        :return: The loaded module.
        :rtype: Plugin
        """
        Remote.clear()
        Actions.clear()
        Initializer.clear()
        plugin = Plugin(name, descriptor)
        Plugin.add(plugin)
        try:
            path = descriptor.main.plugin
            if path:
                plugin.impl = __import__(path, {}, {}, [path.split('.')[-1]])
                Plugin.add(plugin, path)
            else:
                path = PluginLoader.find_plugin(name)
                plugin.impl = imp.load_source(name, path)

            log.info('plugin [%s] loaded using: %s', name, path)

            for fn in Remote.find(plugin.impl.__name__):
                fn.gofer.plugin = plugin
            if plugin.enabled():
                collated = Remote.collated()
                collated += PluginLoader.BUILTINS
                plugin.dispatcher += collated
                plugin.actions = Actions.collated()
                plugin.extend()
                Initializer.run()
            return plugin
        except Exception:
            Plugin.delete(plugin)
            log.exception('plugin "%s", import failed', name)
