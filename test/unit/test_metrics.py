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

from unittest import TestCase
from datetime import datetime

from mock import patch

from gofer.metrics import Timer, timestamp


class TestUtils(TestCase):

    @patch('gofer.metrics.datetime')
    def test_timestamp(self, dt):
        dt.utcnow.return_value = datetime(2014, 12, 25, 9, 30, 0)
        ts = timestamp()
        self.assertEqual(ts, '2014-12-25T09:30:00Z')


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

    def duration(self):
        t = Timer()
        t.started = 10.0
        t.stopped = 100.0
        self.assertEqual(t.duration(), 90.0)

    def test_unicode(self):
        t = Timer()
        # not started
        self.assertEqual(unicode(t), 'not-running')
        # started but not stopped
        t.started = 1
        self.assertEqual(unicode(t), 'started: %d (running)' % t.started)
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
        self.assertEqual(str(t), 'not-running')
        # started but not stopped
        t.started = 1
        self.assertEqual(str(t), 'started: %d (running)' % t.started)
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