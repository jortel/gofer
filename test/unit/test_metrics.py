# Copyright (c) 2014 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import sys
import isodate

from unittest import TestCase
from datetime import datetime, timedelta

from mock import patch, Mock

from gofer.metrics import Timestamp
from gofer.metrics import Timer, Timed, Memory
from gofer.metrics import Writer, LogWriter
from gofer.metrics import timed


class TestTimestamp(TestCase):

    NOW_ST = '2014-12-25T09:30:00Z'
    NOW_DT = datetime(2014, 12, 25, 9, 30, 0, tzinfo=isodate.UTC)

    @patch('gofer.metrics.datetime')
    def test_now(self, dt):
        dt.utcnow.return_value = TestTimestamp.NOW_DT
        self.assertEqual(Timestamp.now(), TestTimestamp.NOW_ST)

    def test_parse(self):
        self.assertEqual(TestTimestamp.NOW_DT, Timestamp.parse(TestTimestamp.NOW_ST))

    @patch('gofer.metrics.datetime')
    def test_in_past(self, dt):
        dt.utcnow.return_value = TestTimestamp.NOW_DT
        _dt = TestTimestamp.NOW_DT - timedelta(minutes=10)
        s = isodate.strftime(_dt, isodate.DT_EXT_COMPLETE)
        self.assertTrue(Timestamp.in_past(s))

    @patch('gofer.metrics.datetime')
    def test_in_future(self, dt):
        dt.utcnow.return_value = TestTimestamp.NOW_DT
        _dt = TestTimestamp.NOW_DT + timedelta(minutes=10)
        s = isodate.strftime(_dt, isodate.DT_EXT_COMPLETE)
        self.assertFalse(Timestamp.in_past(s))


class TestTimer(TestCase):

    def test_init(self):
        t = Timer()
        self.assertEqual(t.started, 0)
        self.assertEqual(t.stopped, 0)

    @patch('time.time')
    def test_start(self, _time):
        _time.return_value = 10.0
        t = Timer()
        t.start()
        self.assertEqual(t.started, 10.0)
        self.assertEqual(t.stopped, 0)

    @patch('time.time')
    def test_stop(self, _time):
        _time.return_value = 20.0
        t = Timer()
        t.started = 10.0
        t.stop()
        self.assertEqual(t.started, 10.0)
        self.assertEqual(t.stopped, 20.0)

    def test_duration(self):
        t = Timer()
        t.started = 10.0
        t.stopped = 100.0
        self.assertEqual(t.duration(), 90.0)

    def test_unicode(self):
        t = Timer()
        # not started
        self.assertEqual(unicode(t), 'idle')
        # started but not stopped
        t.started = 1
        self.assertEqual(unicode(t), 'started')
        # milliseconds
        t.started = 0.10
        t.stopped = 0.25
        self.assertEqual(unicode(t), '150 (ms)')
        # seconds
        t.started = 10.0
        t.stopped = 25.0
        self.assertEqual(unicode(t), '15.000 (seconds)')
        # minutes
        t.started = 10.0
        t.stopped = 100.0
        self.assertEqual(unicode(t), '1.500 (minutes)')

    def test_str(self):
        t = Timer()
        # not started
        self.assertEqual(str(t), 'idle')
        # started but not stopped
        t.started = 1
        self.assertEqual(str(t), 'started')
        # milliseconds
        t.started = 0.10
        t.stopped = 0.25
        self.assertEqual(str(t), '150 (ms)')
        # seconds
        t.started = 10.0
        t.stopped = 25.0
        self.assertEqual(str(t), '15.000 (seconds)')
        # minutes
        t.started = 10.0
        t.stopped = 100.0
        self.assertEqual(str(t), '1.500 (minutes)')

    def test_context(self):
        t = Timer()
        t = t.__enter__()
        self.assertTrue(t.started > 0)
        self.assertEqual(t.stopped, 0)
        t.__exit__()
        self.assertTrue(t.stopped > 0)


class TestDecorator(TestCase):

    def test_timed(self):
        @timed
        def fn(a, b):
            return a * b
        r = fn(2, 10)
        self.assertEqual(r, 20)

    def test_timed_with_writer(self):
        @timed(writer=Writer())
        def fn(a, b):
            return a * b
        r = fn(2, 10)
        self.assertEqual(r, 20)

    def test_timed_with_log_writer(self):
        @timed(writer=LogWriter(Mock()))
        def fn(a, b):
            return a * b
        r = fn(2, 10)
        self.assertEqual(r, 20)


class TestTimed(TestCase):

    def test_context(self):
        writer = Mock()
        with Timed(writer) as _timed:
            pass
        self.assertTrue(writer.called)
        self.assertTrue(_timed.timer.started > 0)
        self.assertTrue(_timed.timer.stopped > 0)


class TestMemory(TestCase):

    def test_sizeof_string(self):
        thing = '123'
        n = sys.getsizeof(thing)
        self.assertEqual(Memory._sizeof(thing, set()), n)

    def test_sizeof_list(self):
        thing = ['123', '234']
        n = sys.getsizeof(thing)
        for x in thing:
            n += sys.getsizeof(x)
        self.assertEqual(Memory._sizeof(thing, set()), n)

    def test_sizeof_dict(self):
        thing = {'A': 1, 'B': 2}
        n = sys.getsizeof(thing)
        for x in thing:
            n += sys.getsizeof(x)
        for x in thing.values():
            n += sys.getsizeof(x)
        self.assertEqual(Memory._sizeof(thing, set()), n)

    def test_sizeof_object(self):
        class A:
            def __init__(self):
                self.name = 'elmer'
                self.age = 10
        thing = A()
        n = sys.getsizeof(thing)
        n += sys.getsizeof(thing.__dict__)
        for x in thing.__dict__:
            n += sys.getsizeof(x)
        for x in thing.__dict__.values():
            n += sys.getsizeof(x)
        self.assertEqual(Memory._sizeof(thing, set()), n)

    def test_sizeof_history(self):
        thing = 1
        history = set()
        history.add(id(thing))
        self.assertEqual(Memory._sizeof(thing, history), 0)

    def test_sizeof(self):
        s = Memory.sizeof(1)
        self.assertTrue(isinstance(s, str))
        self.assertTrue(len(s))

    def test_sizeof_not_formatted(self):
        n = Memory.sizeof(1, False)
        self.assertTrue(isinstance(n, int))
        self.assertEqual(n, sys.getsizeof(1))

    def test_format(self):
        self.assertEqual(Memory.format(20), '20')
        self.assertEqual(Memory.format(2000), '2 kB')
        self.assertEqual(Memory.format(2000000), '2 mB')
        self.assertEqual(Memory.format(2000000000), '2 gB')
