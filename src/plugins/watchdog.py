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

from gofer import NAME
from gofer.decorators import *
from gofer.agent.plugin import Plugin
from gofer.rmi.async import WatchDog as Impl
from logging import getLogger

log = getLogger(__name__)
plugin = Plugin.find(__name__)

JOURNAL = '/var/lib/%s/journal/watchdog' % NAME


class WatchDog:
    
    def __init__(self):
        self.__impl = Impl()
        self.__impl.journal(JOURNAL)
    
    @remote
    def track(self, sn, replyto, any, timeout):
        return self.__impl.track(sn, replyto, any, timeout)
    
    @remote
    def hack(self, sn):
        return self.__impl.hack(sn)
    
    @remote
    @action(seconds=1)
    def process(self):
        self.__impl.process()

