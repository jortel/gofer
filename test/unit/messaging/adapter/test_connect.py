# Copyright (c) 2015 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# amqp://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from unittest import TestCase

from mock import patch, Mock

from gofer.messaging.adapter.connect import retry, DELAY, DELAY_MULTIPLIER


class ConnectError(Exception):
    pass


class TestRetry(TestCase):

    @patch('gofer.messaging.adapter.connect.sleep')
    def test_open(self, sleep):
        fn = Mock()
        connection = Mock(retry=True)
        fx = retry(ConnectError)(fn)
        fx(connection)
        fn.assert_called_once_with(connection)
        self.assertFalse(sleep.called)

    @patch('gofer.messaging.adapter.connect.sleep')
    def test_open_failed_no_retry(self, sleep):
        fn = Mock()
        fn.side_effect = [ConnectError]
        connection = Mock(retry=False)
        fx = retry(ConnectError)(fn)
        self.assertRaises(ConnectError, fx, connection)
        self.assertFalse(sleep.called)
        fn.assert_called_once_with(connection)

    @patch('gofer.messaging.adapter.connect.sleep')
    def test_retried(self, sleep):
        fn = Mock()
        fn.side_effect = [ConnectError, ConnectError, None]
        connection = Mock(retry=True)
        fx = retry(ConnectError)(fn)
        fx(connection)
        self.assertEqual(
            sleep.call_args_list,
            [
                ((DELAY,), {}),
                ((DELAY * DELAY_MULTIPLIER,), {}),
            ])
        self.assertEqual(
            fn.call_args_list,
            [
                ((connection,), {}),
                ((connection,), {}),
                ((connection,), {}),
            ])

    @patch('gofer.messaging.adapter.connect.RETRIES', 2)
    @patch('gofer.messaging.adapter.connect.sleep')
    def test_exceeded(self, sleep):
        fn = Mock()
        fn.side_effect = [ConnectError, ConnectError, ConnectError]
        connection = Mock(retry=True)
        fx = retry(ConnectError)(fn)
        self.assertRaises(ConnectError, fx, connection)
        self.assertEqual(
            sleep.call_args_list,
            [
                ((DELAY,), {}),
                ((DELAY * DELAY_MULTIPLIER,), {}),
            ])
        self.assertEqual(
            fn.call_args_list,
            [
                ((connection,), {}),
                ((connection,), {}),
                ((connection,), {}),
            ])
