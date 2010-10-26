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

from gopher.agent.config import Config
from logging import getLogger

log = getLogger(__name__)


class Identity:
    """
    Agent identity
    @ivar plugin: The identity plugin
    @type plugin: An identity function
    """
    plugins = []
        
    def getuuid(self):
        """
        Get the agent UUID.
        @return: The UUID.
        @rtype: str
        """
        for plugin in self.plugins:
            try:
                return plugin.getuuid()
            except:
                log.error('plugin (%s) failed', plugin, exc_info=True)
        cfg = Config()
        return cfg.main.uuid


def identity(cls):
    """
    Identity decorator
    @param cls: A class that provides identity
    @type cls: plugin class
    """
    plugin = cls()
    Identity.plugins.append(plugin)
    return cls
