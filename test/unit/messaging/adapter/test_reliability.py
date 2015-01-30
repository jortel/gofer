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

from unittest import TestCase

from mock import patch, Mock

from gofer.messaging.adapter.reliability import blocking, DELAY, DELAY_MULTIPLIER
from gofer.messaging.adapter.reliability import MINUTE, DAY, MONTH, YEAR


class TestConstants(TestCase):

    def test(self):
        self.assertEqual(MINUTE, 60)
        self.assertEqual(DAY, 86400)
        self.assertEqual(MONTH, 0x278D00)
        self.assertEqual(YEAR, 0x1E13380)


class TestBlockingDecorator(TestCase):

    def test_call(self):
        fn = Mock()
        _fn = blocking(fn)
        reader = Mock()
        timeout = 10
        message = _fn(reader, timeout)
        fn.assert_called_once_with(reader, timeout)
        self.assertEqual(message, fn.return_value)

    @patch('gofer.messaging.adapter.reliability.sleep')
    def test_delay(self, sleep):
        received = [
            None,
            None,
            Mock()]
        fn = Mock(side_effect=received)
        _fn = blocking(fn)
        reader = Mock()
        timeout = 10
        message = _fn(reader, timeout)
        self.assertEqual(
            fn.call_args_list,
            [
                ((reader, float(timeout)), {}),
                ((reader, float(timeout - DELAY)), {}),
                ((reader, float(timeout - (DELAY + (DELAY * DELAY_MULTIPLIER)))), {})
            ])
        self.assertEqual(
            sleep.call_args_list,
            [
                ((DELAY,), {}),
                ((DELAY * DELAY_MULTIPLIER,), {})
            ])
        self.assertEqual(message, received[-1])

    @patch('gofer.messaging.adapter.reliability.sleep')
    def test_call_blocking(self, sleep):
        fn = Mock(return_value=None)
        _fn = blocking(fn)
        reader = Mock()
        timeout = 10
        message = _fn(reader, timeout)
        self.assertEqual(message, None)
        total = 0.0
        for call in sleep.call_args_list:
            total += call[0][0]
        self.assertEqual(int(total), timeout)
        self.assertEqual(fn.call_count, 43)
