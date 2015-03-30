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

import imp
import os
import sys

from logging import getLogger
from threading import RLock

from gofer import Singleton, synchronized, NAME
from gofer.agent.config import PLUGIN_SCHEMA, PLUGIN_DEFAULTS
from gofer.agent.decorator import Actions
from gofer.agent.decorator import Delegate
from gofer.agent.rmi import Scheduler
from gofer.agent.whiteboard import Whiteboard
from gofer.common import nvl, mkdir
from gofer.common import released
from gofer.config import Config, Graph, Reader, get_bool
from gofer.messaging import Document, Connector, Node, Queue, Exchange
from gofer.messaging import NotFound
from gofer.rmi.consumer import RequestConsumer
from gofer.rmi.decorator import Remote
from gofer.rmi.dispatcher import Dispatcher
from gofer.threadpool import ThreadPool


log = getLogger(__name__)


def attach(fn):
    def _fn(plugin):
        def call():
            if plugin.url and plugin.node:
                fn(plugin)
        plugin.pool.run(call)
    return _fn


class Builtin(object):
    """
    The builtin plugin.
    """

    PATH = '/tmp/%s/.builtin.conf' % NAME

    NAME = '__builtin__'

    DESCRIPTOR = """
    [main]
    enabled=1
    name=%s
    threads=3
    plugin=gofer.agent.builtin
    accept=*
    """ % NAME

    @staticmethod
    def install():
        """
        Install the descriptor.
        """
        mkdir(os.path.dirname(Builtin.PATH))
        fp = open(Builtin.PATH, 'w+')
        try:
            for line in Builtin.DESCRIPTOR.split('\n'):
                fp.write(line.strip())
                fp.write('\n')
        finally:
            fp.close()

    @staticmethod
    def find():
        """
        Find this plugin.
        :return: This plugin.
        :rtype: Plugin
        """
        container = Container()
        return container.find(Builtin.NAME)


class Container(object):
    """
    Plugin container.
    """

    __metaclass__ = Singleton

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

    @synchronized
    def load(self, path):
        """
        Load the plugin at the specified path.
        :param path: The absolute path to the descriptor.
        :type path: str
        """
        if path in self.plugins:
            raise ValueError('plugin: %s, already loaded' % path)
        plugin = PluginLoader.load(path)
        if plugin:
            plugin.start()
        else:
            raise Exception('failed')

    @synchronized
    def reload(self, path):
        """
        Reload the plugin at the specified path.
        :param path: The absolute path to the descriptor or a plugin name.
        :type path: str
        """
        if path not in self.plugins:
            raise ValueError('plugin: %s, not-found' % path)
        plugin = self.find(path)
        if plugin:
            plugin.reload()
        else:
            raise Exception('failed')

    @synchronized
    def unload(self, path):
        """
        Unload the plugin at the specified path.
        :param path: The absolute path to the descriptor or a plugin name.
        :type path: str
        """
        if path not in self.plugins:
            raise ValueError('plugin: %s, not-found' % path)
        plugin = self.find(path)
        if plugin:
            plugin.unload()
        else:
            raise Exception('failed')


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
        if not plugin.impl:
            # not loaded
            return
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
        self.delegate = Delegate()
        self.authenticator = None
        self.consumer = None

    @property
    def name(self):
        return self.cfg.main.name

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
    def node(self):
        model = BrokerModel(self)
        return model.node

    @property
    def forward(self):
        _list = self.cfg.main.forward
        _list = [p.strip() for p in _list.split(',')]
        _list.append(Builtin.NAME)
        return set(_list)

    @property
    def accept(self):
        _list = self.cfg.main.accept
        _list = [p.strip() for p in _list.split(',')]
        return set(_list)

    @property
    def is_started(self):
        return self.scheduler.is_alive()

    @synchronized
    def start(self):
        """
        Start the plugin.
        - attach
        - start scheduler
        """
        if self.is_started:
            # already started
            return
        self.attach()
        self.scheduler.start()

    @synchronized
    def shutdown(self, teardown=True):
        """
        Shutdown the plugin.
        - detach
        - shutdown the thread pool.
        - shutdown the scheduler.
        :param teardown: Teardown the broker model.
        :type teardown: bool
        :return: List of pending requests.
        :rtype: list
        """
        if not self.is_started:
            # not started
            return []
        self.detach(teardown)
        pending = self.pool.shutdown()
        self.scheduler.shutdown()
        self.scheduler.join()
        return pending

    @synchronized
    def refresh(self):
        """
        Refresh the AMQP configurations using the plugin configuration.
        """
        connector = Connector(self.url)
        messaging = self.cfg.messaging
        connector.ssl.ca_certificate = messaging.cacert
        connector.ssl.client_key = messaging.clientkey
        connector.ssl.client_certificate = messaging.clientcert
        connector.ssl.host_validation = messaging.host_validation
        connector.add()

    @attach
    @synchronized
    def attach(self):
        """
        Attach (connect) to AMQP connector using the specified uuid.
        """
        self.detach(False)
        self.refresh()
        model = BrokerModel(self)
        model.setup()
        node = Node(model.queue)
        consumer = RequestConsumer(node, self)
        consumer.authenticator = self.authenticator
        consumer.start()
        self.consumer = consumer
        log.info('plugin:%s, attached => %s', self.name, self.node)

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
        log.info('plugin:%s, detached [%s]', self.name, self.node)
        if teardown:
            model = BrokerModel(self)
            model.teardown()

    def provides(self, name):
        """
        Get whether the plugin provides the name.
        :param name: A class name.
        :type name: str
        :return: True if provides.
        :raise: bool
        """
        return self.dispatcher.provides(name)

    def dispatch(self, request):
        """
        Dispatch (invoke) the specified RMI request.
        :param request: An RMI request
        :type request: gofer.Document
        :return: The RMI returned.
        """
        call = Document(request.request)
        dispatcher = self.dispatcher
        if not self.provides(call.classname):
            for plugin in Plugin.all():
                if not plugin.provides(call.classname):
                    # not provided
                    continue
                valid = set()
                valid.add('*')
                valid.add(plugin.name)
                if not valid.intersection(self.forward):
                    # (forwarding) not approved
                    continue
                valid = set()
                valid.add('*')
                valid.add(self.name)
                if not valid.intersection(plugin.accept):
                    # (accept) not approved
                    continue
                dispatcher = plugin.dispatcher
                break
        return dispatcher.dispatch(request)

    @synchronized
    def load(self):
        """
        Load the plugin.
        """
        self.delegate.loaded()
        path = self.cfg.messaging.authenticator
        if not path:
            # not configured
            return
        path = path.split('.')
        mod = '.'.join(path[:-1])
        mod = __import__(mod, {}, {}, [path[-1]])
        self.authenticator = mod.Authenticator()

    @synchronized
    def unload(self):
        """
        Unload the plugin.
        - Detach.
        - Delete the plugin.
        - Abort scheduled requests.
        - Plugin shutdown.
        - Purge pending requests.
        """
        Plugin.delete(self)
        self.shutdown()
        self.delegate.unloaded()
        self.scheduler.pending.delete()
        log.info('plugin:%s, unloaded', self.name)

    @synchronized
    def reload(self):
        """
        Reload the plugin.
        - Detach.
        - Delete the plugin.
        - Abort scheduled requests.
        - Plugin shutdown.
        - Reload plugin.
        - Reschedule pending requests to reloaded plugin.
        """
        Plugin.delete(self)
        pending = self.shutdown(False)
        self.delegate.unloaded()
        plugin = PluginLoader.load(self.path)
        if plugin:
            for call in pending:
                task = call.fn
                task.plugin = self
                plugin.pool.run(task)
            plugin.start()
        else:
            for call in pending:
                task = call.fn
                task.commit()
        log.info('plugin:%s, reloaded', self.name)
        return plugin


class BrokerModel(object):
    """
    Provides AMQP broker model management.
    :ivar plugin: A gofer plugin.
    :type plugin: Plugin
    """

    @staticmethod
    def split(node):
        """
        Split the AMQP node specification.
        Format: <exchange>/<queue|key> where exchange is optional.
        :param node: A node specification.
        :type node: str
        :return: tuple of: (exchange, queue)
        :rtype tuple
        """
        if node:
            parts = node.split('/', 1)
            if len(parts) == 2:
                return parts
            else:
                return None, parts[0]
        else:
            return None, None

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
    def node(self):
        return self.cfg.node or self.cfg.queue or self.plugin.uuid

    @property
    def exchange(self):
        return BrokerModel.split(self.node)[0]

    @property
    def queue(self):
        return BrokerModel.split(self.node)[1]

    @released
    def setup(self):
        """
        Setup the broker model.
        """
        if not self.managed:
            # not managed
            return
        url = self.plugin.url
        queue = Queue(self.queue)
        queue.auto_delete = self.expiration > 0
        queue.expiration = self.expiration
        queue.declare(url)
        if self.exchange:
            exchange = Exchange(self.exchange)
            exchange.bind(queue, url)

    @released
    def teardown(self):
        """
        Teardown the broker model.
        """
        if self.managed < 2:
            return
        try:
            url = self.plugin.url
            queue = Queue(self.queue)
            queue.purge(url)
            queue.delete(url)
        except NotFound:
            pass


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

    @staticmethod
    def load_all():
        """
        Load all plugins.
        :return: A list of loaded plugins.
        :rtype: list
        """
        loaded = []
        root = PluginDescriptor.ROOT
        Builtin.install()
        mkdir(root)
        paths = [os.path.join(root, fn) for fn in os.listdir(root)]
        paths = sorted(paths)
        paths.append(Builtin.PATH)
        for path in paths:
            _, ext = os.path.splitext(path)
            if ext not in Reader.EXTENSION:
                continue
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

            plugin.dispatcher += Remote.collated()
            plugin.actions = Actions.collated()
            plugin.delegate = Delegate()
            plugin.load()
            return plugin
        except Exception:
            log.exception('plugin:%s, import failed', plugin.name)
            Plugin.delete(plugin)
