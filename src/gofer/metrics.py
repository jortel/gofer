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
The *metrics* module defines classes and other resources
designed for collecting and reporting performance metrics.
"""

import time

from math import modf
from threading import local as Local
from datetime import datetime

from gofer.common import utf8


def timestamp():
    dt = datetime.utcnow()
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ')


class Timer(object):

    def __init__(self, name='', started=0, stopped=0):
        self.name = name
        self.started = started
        self.stopped = stopped

    def start(self):
        self.started = time.time()
        self.stopped = 0
        return self

    def stop(self):
        if self.started > 0:
            self.stopped = time.time()
        return self

    def duration(self):
        return self.stopped - self.started

    def __enter__(self):
        self.start()
        TimerContext.current().add(self)
        return self

    def __exit__(self, *unused):
        self.stop()

    def __unicode__(self):
        if self.started == 0:
            return 'idle'
        if self.started > 0 and self.stopped == 0:
            return 'started'
        duration = self.duration()
        jmod = lambda m: (m[1], m[0]*1000)
        if duration < 1:
            ms = (duration * 1000)
            return '%d (ms)' % ms           
        if duration < 60:
            m = modf(duration)
            return '%d.%.3d (seconds)' % jmod(m)
        m = modf(duration/60)
        return '%d.%.3d (minutes)' % jmod(m)

    def __str__(self):
        return utf8(self)


class TimerContext(object):

    _inst = Local()

    @staticmethod
    def list():
        try:
            return TimerContext._inst.list
        except AttributeError:
            _list = []
            TimerContext._inst.list = _list
            return _list

    @staticmethod
    def pop():
        _list = TimerContext.list()
        return _list.pop()

    @staticmethod
    def current():
        try:
            _list = TimerContext.list()
            return _list[-1]
        except IndexError:
            return DeadContext()

    def __init__(self, push=True):
        self.timer = []
        if push:
            self.push()

    def push(self):
        _list = TimerContext.list()
        _list.append(self)
        return self

    def add(self, timer):
        self.timer.append(timer)

    def __enter__(self):
        TimerContext.push(self)
        return self

    def __exit__(self, *unused):
        TimerContext.pop()

    def __iter__(self):
        return iter(self.timer)

    def __len__(self):
        return len(self.timer)


class DeadContext(TimerContext):

    def push(self):
        pass

    def add(self, timer):
        return self


def timed(fn):
    def _fn(*args, **kwargs):
        with Timer('{0}()'.format(fn.__name__)):
            return fn(*args, **kwargs)
    return _fn
