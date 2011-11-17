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

from yum import YumBase
from yum.plugins import TYPE_CORE, TYPE_INTERACTIVE
from gofer.decorators import *
from gofer.agent.plugin import Plugin
from logging import getLogger, Logger

log = getLogger(__name__)
plugin = Plugin.find(__name__)


class Yum(YumBase):
    """
    Provides custom configured yum object.
    """

    def __init__(self, importkeys=False):
        """
        @param importkeys: Allow the import of GPG keys.
        @type importkeys: bool
        """
        YumBase.__init__(self)
        self.preconf.plugin_types = (TYPE_CORE, TYPE_INTERACTIVE)
        self.conf.assumeyes = importkeys

    def registerCommand(self, command):
        """
        Implemented so TYPE_INTERACTIVE can be loaded.
        Commands ignored.
        """
        pass
    
    def cleanLoggers(self):
        """
        Clean handlers leaked by yum.
        """
        for n,lg in Logger.manager.loggerDict.items():
            if not n.startswith('yum.'):
                continue
            for h in lg.handlers:
                lg.removeHandler(h)
    
    def close(self):
        """
        This should be handled by __del__() but YumBase
        objects never seem to completely go out of scope and
        garbage collected.
        """
        YumBase.close(self)
        self.closeRpmDB()
        self.cleanLoggers()
#
# API
#

class Package:
    """
    Package management.
    """
    
    def __init__(self, apply=True, importkeys=False):
        """
        @param apply: Apply changes (not dry-run).
        @type apply: bool
        @param importkeys: Allow the import of GPG keys.
        @type importkeys: bool
        """
        self.apply = apply
        self.importkeys = importkeys

    @remote
    @pam(user='root')
    def install(self, names):
        """
        Install packages by name.
        @param names: A list of package names.
        @type names: [str,]
        @return: A list of installed packages
        @rtype: list
        """
        installed = []
        yb = Yum(self.importkeys)
        try:
            for info in names:
                yb.install(pattern=info)
            for t in yb.tsInfo:
                installed.append(str(t.po))
            if installed and self.apply:
                yb.resolveDeps()
                yb.processTransaction()
        finally:
            yb.close()
        return installed

    @remote
    @pam(user='root')
    def uninstall(self, names):
        """
        Uninstall (erase) packages by name.
        @param names: A list of package names to be removed.
        @type names: list
        @return: A list of erased packages.
        @rtype: list
        """
        erased = []
        yb = Yum()
        try:
            for info in names:
                yb.remove(pattern=info)
            for t in yb.tsInfo:
                erased.append(str(t.po))
            if erased and self.apply:
                yb.resolveDeps()
                yb.processTransaction()
        finally:
            yb.close()
        return erased
            
    @remote
    @pam(user='root')
    def update(self, names=None):
        """
        Update installed packages.
        When (names) is not specified, all packages are updated.
        @param names: A list of package names.
        @type names: [str,]
        @return: A list of updates (pkg,{updates=[],obsoletes=[]})
        @rtype: list
        """
        updated = []
        yb = Yum(self.importkeys)
        try:
            if names:
                for info in names:
                    yb.update(pattern=info)
            else:
                yb.update()
            for t in yb.tsInfo:
                u = self.updinfo(t)
                if not u:
                    continue
                updated.append(u)
            if updated and self.apply:
                yb.resolveDeps()
                yb.processTransaction()
        finally:
            yb.close()
        return updated
    
    def updinfo(self, t):
        """
        Description of an update transaction.
        @param t: A yum transaction.
        @type t: Transaction
        @return: A tuple (pkg,{updates=[],obsoletes=[]})
        """
        p = str(t.po)
        u = [str(u) for u in t.updates]
        o = [str(o) for o in t.obsoletes]
        if u or o:
            d = dict(updates=u, obsoletes=o)
            return (p, d)
        else:
            return None


class PackageGroup:
    """
    PackageGroup management.
    """
    
    def __init__(self, apply=True, importkeys=False):
        """
        @param apply: Apply changes (not dry-run).
        @type apply: bool
        @param importkeys: Allow the import of GPG keys.
        @type importkeys: bool
        """
        self.apply = apply
        self.importkeys = importkeys

    @remote
    @pam(user='root')
    def install(self, names):
        """
        Install package groups by name.
        @param names: A list of package group names.
        @type names: list
        @return: A dict of packages that were installed by group.
        @rtype: dict 
        """
        installed = {}
        yb = Yum(self.importkeys)
        try:
            for name in names:
                packages = yb.selectGroup(name)
                if packages:
                    installed[name] = [str(t.po) for t in packages]
            if installed and self.apply:
                yb.resolveDeps()
                yb.processTransaction()
        finally:
            yb.close()
        return installed

    @remote
    @pam(user='root')
    def uninstall(self, names):
        """
        Uninstall package groups by name.
        @param names: A list of package group names.
        @type names: [str,]
        @return: A dict of erased packages by group.
        @rtype: list
        """
        removed = {}
        yb = Yum()
        try:
            for name in names:
                packages = yb.groupRemove(name)
                if packages:
                    removed[name] = [str(t.po) for t in packages]
            if removed and self.apply:
                yb.resolveDeps()
                yb.processTransaction()
        finally:
            yb.close()
        return removed
