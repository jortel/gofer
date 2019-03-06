# Copyright (c) 2015 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Jeff Ortel (jortel@redhat.com)

from time import sleep
from logging import getLogger

from qpid.messaging import NotFound as _NotFound
from qpid.messaging import ConnectionError, LinkError

from gofer.common import Thread
from gofer.messaging.adapter.model import NotFound


log = getLogger(__name__)


DELAY = 10   # seconds


def reliable(fn):
    def _fn(thing, *args, **kwargs):
        repair = lambda: None
        while not Thread.aborted():
            try:
                repair()
                return fn(thing, *args, **kwargs)
            except _NotFound as e:
                raise NotFound(*e.args)
            except LinkError as le:
                log.warning(str(le))
                repair = thing.repair
                sleep(DELAY)
            except ConnectionError as pe:
                log.warning(str(pe))
                repair = thing.repair
                sleep(DELAY)
    return _fn
