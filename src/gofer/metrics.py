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

import sys
import time

from math import modf
from datetime import datetime


def timestamp():
    dt = datetime.utcnow()
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ')


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

    def __str__(self):
        def jmod(m):
            return int(m[1]), int(m[0] * 1000)
        if self.started == 0:
            return 'idle'
        if self.started > 0 and self.stopped == 0:
            return 'started'
        duration = self.duration()
        if duration < 1:
            ms = int(duration * 1000)
            return '{} (ms)'.format(ms)
        if duration < 60:
            m = modf(duration)
            return '{}.{:03d} (seconds)'.format(*jmod(m))
        m = modf(duration/60)
        return '{}.{:03d} (minutes)'.format(*jmod(m))

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *unused):
        self.stop()


class Memory(object):

    @staticmethod
    def format(n_bytes):
        kb = 1000
        mb = kb * 1000
        gb = mb * 1000
        if n_bytes > gb:
            return '{} gB'.format(int(n_bytes / gb))
        if n_bytes > mb:
            return '{} mB'.format(int(n_bytes / mb))
        if n_bytes > kb:
            return '{} kB'.format(int(n_bytes / kb))
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
