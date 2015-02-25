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
import sys
import inspect

from threading import RLock
from logging import getLogger

from gofer import NAME, synchronized
from gofer.common import released
from gofer.rmi.dispatcher import Dispatcher
from gofer.threadpool import ThreadPool
from gofer.rmi.consumer import RequestConsumer
from gofer.rmi.decorators import Remote
from gofer.common import nvl, mkdir
from gofer.config import Config, Graph, Reader, get_bool
from gofer.agent.config import PLUGIN_SCHEMA, PLUGIN_DEFAULTS
from gofer.agent.action import Actions
from gofer.agent.whiteboard import Whiteboard
from gofer.collator import Module
from gofer.messaging import Connector, Queue, Exchange
from gofer.agent.rmi import Scheduler
from gofer.pmon import PathMonitor


log = getLogger(__name__)


def attach(fn):
    def _fn(plugin):
        def call():
            if plugin.url and plugin.uuid:
                fn(plugin)
        plugin.pool.run(call)
    return _fn


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


class Container(object):
    """
    Plugin container.
    """

    def __init__(self):
        self.__mutex = RLock()
        self.plugins = {}

    @synchronized
    def add(self, plugin, *names):
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
            self.plugins[name] = plugin
        self.plugins[plugin.path] = plugin
        return plugin

    @synchronized
    def delete(self, plugin):
        """
        Delete the plugin.
        :param plugin: The plugin to delete.
        :type plugin: Plugin
        """
        for k, v in self.plugins.items():
            if v == plugin:
                del self.plugins[k]
        return plugin

    @synchronized
    def find(self, name):
        """
        Find a plugin by name or path.
        :param name: A plugin name
        :type name: str
        :return: The plugin when found.
        :rtype: Plugin
        """
        return self.plugins.get(name)

    @synchronized
    def all(self):
        """
        Get a unique list of loaded plugins.
        :return: A list of plugins
        :rtype: list
        """
        unique = []
        for p in self.plugins.values():
            if p in unique:
                continue
            unique.append(p)
        return unique


class Plugin(object):
    """
    Represents a plugin.
    :ivar descriptor: descriptor.
    :type descriptor: PluginDescriptor
    :param path: The descriptor path.
    :type path: str
    :ivar pool: The plugin thread pool.
    :type pool: ThreadPool
    :ivar impl: The plugin implementation.
    :ivar impl: module
    :ivar actions: List of: gofer.action.Action.
    :type actions: list
    :ivar dispatcher: The RMI dispatcher.
    :type dispatcher: Dispatcher
    :ivar whiteboard: The plugin whiteboard.
    :type whiteboard: Whiteboard
    :ivar authenticator: The plugin message authenticator.
    :type authenticator: gofer.messaging.auth.Authenticator
    :ivar consumer: An AMQP request consumer.
    :type consumer: gofer.rmi.consumer.RequestConsumer.
    """

    container = Container()
    
    @staticmethod
    def add(plugin, *names):
        """
        Add the plugin.
        :param plugin: The plugin to add.
        :type plugin: Plugin
        :return: The added plugin
        :rtype: Plugin
        """
        Plugin.container.add(plugin, *names)
    
    @staticmethod
    def delete(plugin):
        """
        Delete the plugin.
        :param plugin: The plugin to delete.
        :type plugin: Plugin
        """
        Plugin.container.delete(plugin)
        mod = plugin.impl.__name__
        del sys.modules[mod]
    
    @staticmethod
    def find(name):
        """
        Find a plugin by name or path.
        :param name: A plugin name
        :type name: str
        :return: The plugin when found.
        :rtype: Plugin 
        """
        return Plugin.container.find(name)

    @staticmethod
    def all():
        """
        Get a unique list of loaded plugins.
        :return: A list of plugins
        :rtype: list
        """
        return Plugin.container.all()

    def __init__(self, descriptor, path):
        """
        :param descriptor: The plugin descriptor.
        :type descriptor: PluginDescriptor
        :param path: The plugin descriptor path.
        :type path: str
        """
        self.__mutex = RLock()
        self.descriptor = descriptor
        self.path = path
        self.pool = ThreadPool(int(descriptor.main.threads or 1))
        self.impl = None
        self.actions = []
        self.dispatcher = Dispatcher()
        self.whiteboard = Whiteboard()
        self.scheduler = Scheduler(self)
        self.authenticator = None
        self.consumer = None

    @property
    def name(self):
        return self.cfg.main.name

    @property
    def stream(self):
        return self.name

    @property
    def cfg(self):
        return self.descriptor

    @property
    def uuid(self):
        return self.cfg.messaging.uuid

    @property
    def url(self):
        return self.cfg.messaging.url

    @property
    def enabled(self):
        return get_bool(self.cfg.main.enabled)

    @property
    def connector(self):
        return Connector(self.url)

    @property
    def queue(self):
        model = BrokerModel(self)
        return model.queue

    def start(self):
        """
        Start the plugin.
        - attach
        - start scheduler
        """
        self.attach()
        self.scheduler.start()

    def shutdown(self):
        """
        Shutdown the plugin.
        - shutdown the thread pool.
        - shutdown the scheduler.
        :return: List of pending requests.
        :rtype: list
        """
        pending = self.pool.shutdown()
        self.scheduler.shutdown()
        self.scheduler.join()
        return pending

    def refresh(self):
        """
        Refresh the AMQP configurations using the plugin configuration.
        """
        connector = Connector(self.url)
        messaging = self.cfg.messaging
        connector.ssl.ca_certificate = messaging.cacert
        connector.ssl.client_certificate = messaging.clientcert
        connector.ssl.host_validation = messaging.host_validation
        connector.add()

    @attach
    @synchronized
    def attach(self):
        """
        Attach (connect) to AMQP connector using the specified uuid.
        """
        self.detach(teardown=False)
        self.refresh()
        model = BrokerModel(self)
        queue = model.setup()
        consumer = RequestConsumer(queue, self)
        consumer.authenticator = self.authenticator
        consumer.start()
        self.consumer = consumer
        log.info('plugin:%s queue:%s, attached', self.name, self.uuid)

    @released
    @synchronized
    def detach(self, teardown=True):
        """
        Detach (disconnect) from AMQP connector.
        :param teardown: Teardown the broker model.
        :type teardown: bool
        """
        if not self.consumer:
            # not attached
            return
        self.consumer.shutdown()
        self.consumer.join()
        self.consumer = None
        log.info('plugin:%s queue:%s, detached', self.name, self.uuid)
        if teardown:
            model = BrokerModel(self)
            model.teardown()

    def dispatch(self, request):
        """
        Dispatch (invoke) the specified RMI request.
        :param request: An RMI request
        :type request: gofer.Document
        :return: The RMI returned.
        """
        return self.dispatcher.dispatch(request)

    def unload(self):
        """
        Unload the plugin.
         - Delete the plugin.
         - Abort associated tasks.
         - Detach.
         - Shutdown the pool.
         - Commit (discard) pending work.
        """
        self.detach()
        Plugin.delete(self)
        pending = self.shutdown()
        for call in pending:
            task = call.fn
            task.commit()
        log.info('plugin:%s, unloaded', self.name)

    def reload(self):
        """
        Reload the plugin.
         - Delete the plugin.
         - Abort associated tasks.
         - Detach.
         - Shutdown the pool.
         - Reschedule pending work to reloaded plugin.
        """
        self.detach()
        Plugin.delete(self)
        pending = self.shutdown()
        plugin = PluginLoader.load(self.path)
        if plugin:
            for call in pending:
                task = call.fn
                task.plugin = self
                plugin.pool.run(task)
        else:
            for call in pending:
                task = call.fn
                task.commit()
        log.info('plugin:%s, reloaded', self.name)
        return plugin

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


class BrokerModel(object):
    """
    Provides AMQP broker model management.
    :ivar plugin: A gofer plugin.
    :type plugin: Plugin
    """

    def __init__(self, plugin):
        """
        :param plugin: A gofer plugin.
        :type plugin: Plugin
        """
        self.plugin = plugin

    @property
    def cfg(self):
        return self.plugin.cfg.model

    @property
    def managed(self):
        return int(self.cfg.managed)

    @property
    def expiration(self):
        return int(nvl(self.cfg.expiration, 0))

    @property
    def queue(self):
        return self.cfg.queue or self.plugin.uuid

    @property
    def exchange(self):
        return self.cfg.exchange

    def setup(self):
        """
        Setup the broker model.
        """
        queue = Queue(self.queue)
        if self.managed:
            url = self.plugin.url
            queue = Queue(self.queue)
            queue.auto_delete = self.expiration > 0
            queue.expiration = self.expiration
            queue.declare(url)
            if self.exchange:
                exchange = Exchange(self.exchange)
                exchange.bind(queue, url)
        return queue

    def teardown(self):
        """
        Teardown the broker model.
        """
        if self.managed < 2:
            return
        url = self.plugin.url
        queue = Queue(self.queue)
        queue.purge(url)
        queue.delete(url)


class PluginDescriptor(Graph):
    """
    Provides a plugin descriptor
    """

    ROOT = '/etc/%s/plugins' % NAME
    

class PluginLoader:
    """
    Agent plugins loader.
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
    def load_all():
        """
        Load all plugins.
        :return: A list of loaded plugins.
        :rtype: list
        """
        loaded = []
        mkdir(PluginDescriptor.ROOT)
        files = os.listdir(PluginDescriptor.ROOT)
        for fn in sorted(files):
            _, ext = os.path.splitext(fn)
            if ext not in Reader.EXTENSION:
                continue
            path = os.path.join(PluginDescriptor.ROOT, fn)
            if os.path.isdir(path):
                continue
            plugin = PluginLoader.load(path)
            if plugin:
                loaded.append(plugin)
        return loaded

    @staticmethod
    def load(path):
        """
        Load the specified plugin.
        :param path: A plugin descriptor path.
        :type path: str
        :return: The loaded plugin.
        :rtype: Plugin
        """
        fn = os.path.basename(path)
        name, _ = os.path.splitext(fn)
        default = dict(main=dict(name=name))
        conf = Config(PLUGIN_DEFAULTS, default, path)
        conf.validate(PLUGIN_SCHEMA)
        descriptor = PluginDescriptor(conf)
        plugin = Plugin(descriptor, path)
        if plugin.enabled:
            plugin = Plugin(descriptor, path)
            plugin = PluginLoader._load(plugin)
        else:
            log.warn('plugin:%s, DISABLED', plugin.name)
            plugin = None
        return plugin

    @staticmethod
    def _find(plugin):
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
        reason = '%s, not found in:%s' % (mod, PluginLoader.PATH)
        raise Exception(reason)

    @staticmethod
    def _load(plugin):
        """
        Import a module by file name.
        :param plugin: A plugin to load.
        :type plugin: Plugin
        :return: The loaded plugin.
        :rtype: Plugin
        """
        Remote.clear()
        Actions.clear()
        Initializer.clear()
        Plugin.add(plugin)
        try:
            path = plugin.descriptor.main.plugin
            if path:
                Plugin.add(plugin, path)
                plugin.impl = __import__(path, {}, {}, [path.split('.')[-1]])
            else:
                path = PluginLoader._find(plugin.name)
                plugin.impl = imp.load_source(plugin.name, path)

            log.info('plugin:%s loaded using: %s', plugin.name, path)

            for fn in Remote.find(plugin.impl.__name__):
                fn.gofer.plugin = plugin

            collated = Remote.collated()
            collated += PluginLoader.BUILTINS
            plugin.dispatcher += collated
            plugin.actions = Actions.collated()
            Initializer.run()
            return plugin
        except Exception:
            Plugin.delete(plugin)
            log.exception('plugin:%s, import failed', plugin.name)


class PluginMonitor(object):
    """
    Plugin monitoring.
    :ivar monitor: Path monitor.
    :type monitor: PathMonitor
    """

    def __init__(self):
        self.monitor = PathMonitor()

    def start(self):
        """
        Start monitoring.
        """
        self.monitor.add(PluginDescriptor.ROOT, self.changed)
        for plugin in Plugin.all():
            self.monitor.add(plugin.path, self.changed)
        self.monitor.start()

    def root_changed(self):
        """
        The directory containing plugin descriptors has changed.
        """
        root = PluginDescriptor.ROOT
        loaded = {p.path for p in Plugin.all()}
        for path in [os.path.join(root, name) for name in os.listdir(root)]:
            _, ext = os.path.splitext(path)
            if ext not in Reader.EXTENSION:
                continue
            if path in loaded:
                continue
            self.load(path)

    def file_changed(self, path):
        """
        A file descriptor has been changed/deleted.
        The associated plugin is loaded/reloaded as needed.
        :param path: The path that changed.
        :type path: str
        """
        plugin = Plugin.find(path)
        if os.path.exists(path):
            # load/reload
            if plugin and plugin.enabled:
                plugin.reload()
            else:
                self.load(path)
        else:
            # unload
            self.unload(plugin)

    def changed(self, path):
        """
        A monitored path has changed.
        :param path: The path that changed.
        :type path: str
        """
        log.info('changed: %s', path)
        root = PluginDescriptor.ROOT
        if path == root:
            self.root_changed()
        else:
            self.file_changed(path)

    def unload(self, plugin):
        """
        Unload the plugin.
        :param plugin: The plugin to unload.
        :type plugin: Plugin
        """
        log.info('plugin:%s, unloading', plugin.name)
        plugin.unload()

    def load(self, path):
        """
        Load the plugin at the specified path and begin
        monitoring the path.
        :param path: The path that changed.
        :type path: str
        """
        plugin = PluginLoader.load(path)
        if not plugin:
            # not loaded
            return
        plugin.start()
        self.monitor.add(path, self.changed)

