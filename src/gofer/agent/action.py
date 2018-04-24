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

from logging import getLogger
from datetime import datetime as dt
from datetime import timedelta

from gofer.compat import str
from gofer.common import released


log = getLogger(__name__)


class Action:
    """
    Abstract recurring action (base).
    :ivar name: The action name.
    :type name: str
    :ivar target: The action target.
    :type target: (method|function)
    :ivar interval: The run interval.
    :type interval: dt
    :ivar last: The last run timestamp.
    :type last: datetime
    """

    def __init__(self, name, target, **interval):
        """
        :param name: The action name.
        :type name: str
        :param target: The action target.
        :type target: (method|function)
        :keyword interval: The run interval.
          One of:
            - days
            - seconds
            - minutes
            - hours
            - weeks
        :type interval: dict
        """
        self.name = name
        self.target = target
        self.interval = timedelta(**{k: int(v) for k, v in interval.items()})
        self.last = dt(1900, 1, 1)

    @released
    def __call__(self):
        """
        Invoke the action.
        """
        try:
            _next = self.last + self.interval
            now = dt.utcnow()
            if _next < now:
                self.last = now
                log.debug('perform "%s"', self.name)
                self.target()
        except Exception as e:
            log.exception(e)

    def __eq__(self, other):
        return isinstance(other, Action) and \
            other.name == self.name and \
            other.target and \
            other.interval == self.interval

    def __repr__(self):
        return str(self.name)

    def __str__(self):
        return str(self.name)
