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
Builtin plugin.
"""

import socket

from uuid import uuid4

from gofer.decorators import *
from gofer.agent.plugin import Plugin

from logging import getLogger

log = getLogger(__name__)
plugin = Plugin.find(__name__)


class TestAction:

    @action(hours=36)
    def hello(self):
        plugin = Plugin.find(__name__)
        log.info('Hello:\n%s', plugin.cfg())


class TestAdmin:

    @remote
    def echo(self, thing):
        return thing


@remote
def echo(something):
    return something

#
# Set the uuid to the hostname when not
# specified in the config.
#

if not plugin.getuuid():
    hostname = socket.gethostname()
    uuid = str(uuid4())
    if not hostname.startswith('localhost'):
        uuid = 'admin@%s' % hostname
    plugin.setuuid(uuid)
