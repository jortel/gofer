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
from iniparse import INIConfig as Base
from logging import getLogger

log = getLogger(__name__)


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
            path = os.path.join(cls.ROOT, fn)
            fp = open(path)
            descriptor = cls(fp)
            plugin = fn.split('.')[0]
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
        """
        for plugin, cfg in PluginDescriptor.load():
            enabled = self.__enabled(cfg)
            if not enabled:
                continue
            self.__import(plugin, cfg)
                
    def __enabled(self, cfg):
        """
        Safely validate the plugin is enabled.
        @param cfg: A plugin descriptor.
        @type cfg: L{PluginDescriptor}
        @return: True if enabled.
        @rtype: bool
        """
        try:
            return cfg.main.enabled
        except:
            return False

    def __import(self, plugin, cfg):
        """
        Import a module by file name.
        @param plugin: The plugin (module) name.
        @type plugin: str
        @param cfg: A plugin descriptor.
        @type cfg: L{PluginDescriptor}
        """
        try:
            name = self.__mangled(plugin)
            mod = '%s.py' % plugin
            path = os.path.join(self.ROOT, mod)
            imp.load_source(name, path)
            log.info('plugin "%s", imported as: "%s"', plugin, name)
            Plugin.descriptor[name] = cfg
            Plugin.descriptor[plugin] = cfg
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
