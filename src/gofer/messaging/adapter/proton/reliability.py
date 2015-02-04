# Copyright (c) 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
# Jeff Ortel (jortel@redhat.com)

from time import sleep

from proton import ConnectionException, LinkException, Delivery
from proton.utils import SendException

from gofer.messaging.adapter.reliability import MINUTE


DELAY = 3   # seconds

RESEND_DELAY = 10  # seconds
MAX_RESEND = (MINUTE * 10) / RESEND_DELAY


def reliable(fn):
    def _fn(thing, *args, **kwargs):
        repair = lambda: None
        while True:
            try:
                repair()
                return fn(thing, *args, **kwargs)
            except LinkException:
                sleep(DELAY)
                thing.close()
                repair = thing.open
            except ConnectionException:
                sleep(DELAY)
                thing.close()
                thing.connection.close()
                repair = thing.open
    return _fn


def resend(fn):
    @reliable
    def _fn(thing, *args, **kwargs):
        retry = MAX_RESEND
        delay = RESEND_DELAY
        while retry > 0:
            try:
                return fn(thing, *args, **kwargs)
            except SendException, le:
                if le.state == Delivery.RELEASED:
                    sleep(delay)
                    retry -= 1
                else:
                    raise
    return _fn
