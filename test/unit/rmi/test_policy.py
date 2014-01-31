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
from gofer.rmi.policy import Timeout


class TimeoutTests(TestCase):

    def test_none(self):
        t = Timeout()
        self.assertEqual(t.start, None)
        self.assertEqual(t.duration, None)
        self.assertEqual(t.tuple(), (None, None))

    def test_start_int(self):
        t = Timeout(10)
        self.assertEqual(t.start, 10)
        self.assertEqual(t.duration, None)
        self.assertEqual(t.tuple(), (10, None))

    def test_duration_int(self):
        t = Timeout(None, 10)
        self.assertEqual(t.start, None)
        self.assertEqual(t.duration, 10)
        self.assertEqual(t.tuple(), (None, 10))

    def test_int(self):
        t = Timeout(5, 10)
        self.assertEqual(t.start, 5)
        self.assertEqual(t.duration, 10)
        self.assertEqual(t.tuple(), (5, 10))

    def test_float(self):
        t = Timeout(5.1, 10.1)
        self.assertEqual(t.start, 5)
        self.assertEqual(t.duration, 10)
        self.assertEqual(t.tuple(), (5, 10))

    def test_string(self):
        t = Timeout('5', '10')
        self.assertEqual(t.start, 5)
        self.assertEqual(t.duration, 10)
        self.assertEqual(t.tuple(), (5, 10))

    def test_string_seconds(self):
        t = Timeout('5s', '10s')
        self.assertEqual(t.start, 5)
        self.assertEqual(t.duration, 10)
        self.assertEqual(t.tuple(), (5, 10))

    def test_string_minutes(self):
        t = Timeout('5m', '10m')
        minutes = (5*Timeout.MINUTE, 10*Timeout.MINUTE)
        self.assertEqual(t.start, minutes[0])
        self.assertEqual(t.duration, minutes[1])
        self.assertEqual(t.tuple(), minutes)

    def test_string_hours(self):
        t = Timeout('5h', '10h')
        hours = (5*Timeout.HOUR, 10*Timeout.HOUR)
        self.assertEqual(t.start, hours[0])
        self.assertEqual(t.duration, hours[1])
        self.assertEqual(t.tuple(), hours)

    def test_string_days(self):
        t = Timeout('5d', '10d')
        days = (5*Timeout.DAY, 10*Timeout.DAY)
        self.assertEqual(t.start, days[0])
        self.assertEqual(t.duration, days[1])
        self.assertEqual(t.tuple(), days)

    def test_string_days_no_duration(self):
        t = Timeout(u'5d', None)
        days = (5*Timeout.DAY, None)
        self.assertEqual(t.start, days[0])
        self.assertEqual(t.duration, days[1])
        self.assertEqual(t.tuple(), days)

    def test_errors(self):
        self.assertRaises(TypeError, Timeout, {})
        self.assertRaises(ValueError, Timeout, 'x')
        self.assertRaises(ValueError, Timeout, '10x')
        self.assertRaises(ValueError, Timeout, '')
