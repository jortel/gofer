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
from gofer.decorators import *
from gofer.agent.plugin import Plugin
from logging import getLogger

log = getLogger(__name__)
plugin = Plugin.find(__name__)


def ybcleanup(yb):
    """
    Needed to clean up resources leaked by yum.
    """
    try:
        # close rpm db
        yb.closeRpmDB()
        # hack!  prevent file descriptor leak
        yl = getLogger('yum.filelogging')
        for h in yl.handlers:
            yl.removeHandler(h)
    except Exception, e:
        log.exception(e)
        

class Package:
    """
    Package management.
    """
    @remote
    @pam(user='root')
    def install(self, names, importkeys=False):
        """
        Install packages by name.
        @param names: A list of package names.
        @type names: [str,]
        @param importkeys: Allow YUM to import GPG keys.
        @type importkeys: bool
        @return: A list of installed packages
        @rtype: list
        """
        installed = []
        yb = YumBase()
        yb.conf.assumeyes = importkeys
        try:
            for info in names:
                yb.install(pattern=info)
            if len(yb.tsInfo):
                for t in yb.tsInfo:
                    installed.append(str(t.po))
                yb.resolveDeps()
                yb.processTransaction()
        finally:
            ybcleanup(yb)
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
        yb = YumBase()
        try:
            for info in names:
                yb.remove(pattern=info)
            if len(yb.tsInfo):
                for t in yb.tsInfo:
                    erased.append(str(t.po))
                yb.resolveDeps()
                yb.processTransaction()
            return erased
        finally:
            ybcleanup(yb)


class PackageGroup:
    """
    PackageGroup management.
    """

    @remote
    @pam(user='root')
    def install(self, names, importkeys=False):
        """
        Install package groups by name.
        @param names: A list of package group names.
        @type names: list
        @param importkeys: Allow YUM to install GPG keys.
        @type importkeys: bool
        @return: A dict of packages that were installed by group.
        @rtype: dict 
        """
        installed = {}
        yb = YumBase()
        yb.conf.assumeyes = importkeys
        try:
            for name in names:
                packages = yb.selectGroup(name)
                if packages:
                    installed[name] = [str(t.po) for t in packages]
            if installed:
                yb.resolveDeps()
                yb.processTransaction()
        finally:
            ybcleanup(yb)
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
        yb = YumBase()
        try:
            for name in names:
                packages = yb.groupRemove(name)
                if packages:
                    removed[name] = [str(t.po) for t in packages]
            if removed:
                yb.resolveDeps()
                yb.processTransaction()
            return removed
        finally:
            ybcleanup(yb)
