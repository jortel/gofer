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

"""
Action slass for gofer agent.
"""

import inspect
from gofer.collator import Collator
from datetime import datetime as dt
from datetime import timedelta
from logging import getLogger

log = getLogger(__name__)


class Actions:
    """
    @cvar functions: The list of decorated functions.
    """
    functions = {}
    
    def collated(self):
        collated = []
        c = Collator()
        classes, functions = c.collate(self.functions)
        for c,m in classes.items():
            inst = c()
            for m,d in m:
                m = getattr(inst, m.__name__)
                action = Action(m, **d)
                collated.append(action)
        for m,f in functions.items():
            for f,d in f:
                action = Action(f, **d)
                collated.append(action)
        return collated


def action(**interval):
    """
    Action decorator.
    """
    def decorator(fn):
        Actions.functions[fn] = interval
        return fn
    return decorator


class Action:
    """
    Abstract recurring action (base).
    @ivar target: The action target.
    @type target: (method|function)
    @keyword interval: The run interval.
      One of:
        - days
        - seconds
        - minutes
        - hours
        - weeks
    @ivar last: The last run timestamp.
    @type last: datetime
    """

    def __init__(self, target, **interval):
        """
        @param target: The action target.
        @type target: (method|function)
        @param interval: The run interval (minutes).
        @type interval: timedelta
        """
        self.target = target
        for k,v in interval.items():
            interval[k] = int(v)
        self.interval = timedelta(**interval)
        self.last = dt(1900, 1, 1)

    def name(self):
        """
        Get action name.  Default to class name.
        @return: The action name.
        @rtype: str
        """
        t = self.target
        if inspect.ismethod(t):
            cls = t.im_class
        else:
            cls = t.__module__
        method = t.__name__
        return '%s.%s()' % (cls, method)
    
    def __str__(self):
        return self.name()

    def __call__(self):
        try:
            next = self.last+self.interval
            now = dt.utcnow()
            if next < now:
                self.last = now
                log.debug('perform "%s"', self.name())
                self.target()
        except Exception, e:
            log.exception(e)
