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

from gofer.collator import Collator
from logging import getLogger

log = getLogger(__name__)


class Identity:
    """
    Agent identity
    @ivar plugin: The identity plugin
    @type plugin: An identity function
    """
    plugins = {}
    
    def __init__(self, plugin):
        self.plugin = plugin
        
    def getuuid(self):
        """
        Get the agent UUID.
        @return: The UUID.
        @rtype: str
        """
        fnlist = []
        for name in self.plugin.names():
            fnlist = self.plugins.get(name)
            if fnlist:
                break
        if not fnlist:
            return
        c = Collator()
        classes, functions = c.collate(fnlist)
        for cls,methods in classes.items():
            inst = cls()
            for m,d in methods:
                try:
                    m = getattr(inst, m.__name__)
                    return m()
                except:
                    log.error('%s.%s() failed',
                        cls.__name__,
                        m.__name__,
                        exc_info=True)
        for mod,functions in functions.items():
            for fn,d in functions:
                try:
                    return fn()
                except:
                    log.error('%s.%s() failed',
                        mod.__name__,
                        fn.__name__,
                        exc_info=True)
    

def identity(fn):
    """
    Identity decorator
    @param fn: A method/function that provides identity
    @type fn: callable
    """
    name = fn.__module__
    fnlist = Identity.plugins.get(name)
    if fnlist is None:
        fnlist = []
        Identity.plugins[name] = fnlist
    fnlist.append(fn)
    return fn
