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

"""
Plugin classes.
"""

import os
import sys
import imp
from gofer import *
from gofer.collator import Collator
from gofer.agent.identity import Identity
from gofer.agent.config import Config
from iniparse import INIConfig as Base
from iniparse.config import Undefined
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
        Add the plugin by name and synonyms.
        @param plugin: The plugin to add.
        @type plugin: L{Plugin}
        @return: The added plugin
        @rtype: L{Plugin}
        """
        cls.plugins[plugin.name] = plugin
        for name in plugin.synonyms:
            cls.plugins[name] = plugin
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
        self.synonyms = synonyms
        self.descriptor = descriptor
        
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
        cfg = elf.cfg()
        try:
            return int(cfg.main.enabled)
        except:
            return 0
        
    def getuuid(self):
        """
        Get the plugin's messaging UUID.
        The uuid defined in the plugin descriptor is returned
        when specified.  If not, the plugin's registered identity
        function/method is called and value returend.
        @return: The plugin's messaging UUID.
        @rtype: str
        """
        cfg = self.cfg()
        uuid = cfg.messaging.uuid
        if not isinstance(uuid, (str,int)):
            ident = Identity(self)
            uuid = ident.getuuid()
        return uuid
        
    def cfg(self):
        return self.descriptor


class PluginDescriptor(Base):
    """
    Provides a plugin descriptor
    """
    
    ROOT = '/etc/gofer/plugins'
    
    @classmethod
    def load(cls):
        """
        Load the plugin descriptors.
        @return: A list of descriptors.
        @rtype: list
        """
        lst = []
        for fn in os.listdir(cls.ROOT):
            plugin,ext = fn.split('.',1)
            if not ext in ('.conf'):
                continue
            path = os.path.join(cls.ROOT, fn)
            if os.path.isdir(path):
                continue
            fp = open(path)
            descriptor = cls(fp)
            lst.append((plugin, descriptor))
        return lst


class PluginLoader:
    """
    Agent plugins loader.
    @ivar plugins: A dict of plugins and configuratons
    @type plugins: dict
    """

    ROOT = '/usr/lib/gofer/plugins'

    def __init__(self):
        if not os.path.exists(self.ROOT):
            os.makedirs(self.ROOT)

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
        try:
            name = self.__mangled(plugin)
            mod = '%s.py' % plugin
            path = os.path.join(self.ROOT, mod)
            mod = imp.load_source(name, path)
            log.info('plugin "%s", imported as: "%s"', plugin, name)
            synonyms = []
            if name != plugin:
                synonyms.append(name)
            p = Plugin(plugin, cfg, synonyms=synonyms)
            Plugin.add(p)
            return p
        except:
            log.error(
                'plugin "%s", import failed',
                plugin, 
                exc_info=True)
            
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
