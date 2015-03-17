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

from mock import Mock, patch

from gofer.agent.whiteboard import Whiteboard


class TestWhiteboard(TestCase):

    def test_init(self):
        wb = Whiteboard()
        self.assertTrue(isinstance(wb, Whiteboard))
        self.assertTrue(isinstance(wb._Whiteboard__dict, dict))

    @patch('gofer.agent.whiteboard.RLock', Mock())
    def test_all(self):
        a = 10
        b = 20
        wb = Whiteboard()
        mutex = wb._Whiteboard__mutex
        wb['a'] = a
        wb['b'] = b
        # setting
        self.assertEqual(mutex.acquire.call_count, 2)
        self.assertEqual(mutex.release.call_count, 2)
        self.assertEqual(wb._Whiteboard__dict, {'a': a, 'b': b})
        # get item
        self.assertEqual(wb['a'], a)
        self.assertEqual(wb['b'], b)
        self.assertRaises(KeyError, wb.__getitem__, 'c')
        self.assertEqual(mutex.acquire.call_count, 5)
        self.assertEqual(mutex.release.call_count, 5)
        # get
        self.assertEqual(wb.get('a'), a)
        self.assertEqual(wb.get('b'), b)
        self.assertEqual(wb.get('c'), None)
        self.assertEqual(wb.get('d', 30), 30)
        self.assertEqual(mutex.acquire.call_count, 9)
        self.assertEqual(mutex.release.call_count, 9)
        # update
        wb.update({'e': 40, 'f': 50})
        self.assertEqual(wb._Whiteboard__dict, {'a': a, 'b': b, 'e': 40, 'f': 50})
        self.assertEqual(mutex.acquire.call_count, 10)
        self.assertEqual(mutex.release.call_count, 10)
        # repr
        self.assertEqual(repr(wb), repr(wb._Whiteboard__dict))
        self.assertEqual(mutex.acquire.call_count, 11)
        self.assertEqual(mutex.release.call_count, 11)
        # repr
        self.assertEqual(str(wb), str(wb._Whiteboard__dict))
        self.assertEqual(mutex.acquire.call_count, 13)
        self.assertEqual(mutex.release.call_count, 13)