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

import os
import sys
import time
import inspect

import isodate

from math import modf
from datetime import datetime

from gofer.common import utf8


def timed(fx=None, writer=None):
    def inner(fn):
        def call(*args, **kwargs):
            display = writer or Writer()
            with Timer() as timer:
                retval = fn(*args, **kwargs)
            context = '{0}()'.format(fn.__name__)
            display(context, timer)
            return retval
        return call
    if inspect.isfunction(fx):
        return inner(fx)
    else:
        return inner


class Timestamp(object):

    @staticmethod
    def now():
        dt = datetime.utcnow()
        dt = dt.replace(tzinfo=isodate.UTC)
        return isodate.strftime(dt, isodate.DT_EXT_COMPLETE)

    @staticmethod
    def parse(s):
        return isodate.parse_datetime(s)

    @staticmethod
    def in_past(s):
        dt = datetime.utcnow()
        dt = dt.replace(tzinfo=isodate.UTC)
        return Timestamp.parse(s) < dt


class Timed(object):

    def __init__(self, writer=None):
        self.writer = writer or Writer()
        self.timer = Timer()

    def __enter__(self):
        self.timer.start()
        return self

    def __exit__(self, *unused):
        self.timer.stop()
        frame = inspect.stack()[1]
        context = '{0}:{1}'.format(os.path.basename(frame[1]), frame[2])
        self.writer(context, self.timer)


class Writer(object):

    def __call__(self, context, timer):
        print '\n{0} duration: {1}\n'.format(context, timer)


class LogWriter(Writer):

    def __init__(self, log):
        self.log = log

    def __call__(self, context, timer):
        self.log.info('%s duration: %s', context, timer)


class Timer(object):

    def __init__(self, started=0, stopped=0):
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

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *unused):
        self.stop()

    def __str__(self):
        return utf8(self)


class Memory(object):

    @staticmethod
    def format(n_bytes):
        kb = 1000
        mb = kb * 1000
        gb = mb * 1000
        if n_bytes > gb:
            return '{0} gB'.format(n_bytes / gb)
        if n_bytes > mb:
            return '{0} mB'.format(n_bytes / mb)
        if n_bytes > kb:
            return '{0} kB'.format(n_bytes / kb)
        return str(n_bytes)

    @staticmethod
    def sizeof(thing, formatted=True):
        history = set()
        n_bytes = Memory._sizeof(thing, history)
        del history
        if formatted:
            return Memory.format(n_bytes)
        else:
            return n_bytes

    @staticmethod
    def _sizeof(thing, history):
        thing_id = id(thing)
        if thing_id in history:
            return 0
        history.add(thing_id)
        n_bytes = sys.getsizeof(thing)
        if isinstance(thing, (list, tuple)):
            for v in thing:
                n_bytes += Memory._sizeof(v, history)
        elif isinstance(thing, dict):
            for k in thing:
                n_bytes += Memory._sizeof(k, history)
            for v in thing.values():
                n_bytes += Memory._sizeof(v, history)
        elif hasattr(thing, '__dict__'):
            n_bytes += Memory._sizeof(thing.__dict__, history)
        return n_bytes
