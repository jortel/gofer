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
    plugin = []
        
    def getuuid(self):
        for fn in self.plugin:
            try:
                return fn()
            except:
                log.error('plugin (%s) failed', fn, exc_info=True)
        cfg = Config()
        return cfg.main.uuid
            
    def __str__(self):
        return self.uuid
    

def identity(fn):
    """
    Identity decorator
    @param fn: A function that provides identity
    @type fn: callable
    """
    Identity.plugin.append(fn)
    return fn
