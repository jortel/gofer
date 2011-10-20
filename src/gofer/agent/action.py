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
    
    @classmethod
    def add(cls, fn, interval):
        cls.functions[fn] = interval
    
    @classmethod
    def collated(cls):
        collated = []
        c = Collator()
        classes, functions = c.collate(cls.functions)
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
    
    @classmethod
    def clear(cls):
        """
        Clear the list of actions.
        """
        cls.functions = {}


def action(**interval):
    """
    Action decorator.
    """
    def decorator(fn):
        Actions.add(fn, interval)
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
