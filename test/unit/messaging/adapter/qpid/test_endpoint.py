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

from gofer.devel import ipatch

with ipatch('qpid'):
    from gofer.messaging.adapter.qpid.endpoint import Endpoint, BaseEndpoint


class TestEndpoint(TestCase):

    def test_init(self):
        url = 'test-url'

        # test
        endpoint = Endpoint(url)

        # validation
        self.assertTrue(isinstance(endpoint, BaseEndpoint))
        self.assertEqual(endpoint._channel, None)
        self.assertEqual(endpoint._connection, None)
        self.assertEqual(endpoint.url, url)

    def test_channel(self):
        url = 'test-url'

        # test
        endpoint = Endpoint(url)
        channel = endpoint.channel()

        # validation
        self.assertEqual(channel, endpoint._channel)

    def test_ack(self):
        url = 'test-url'
        message = Mock()

        # test
        endpoint = Endpoint(url)
        endpoint._channel = Mock()
        endpoint.ack(message)

        # validation
        endpoint._channel.acknowledge.assert_called_once_with(message=message)

    def test_ack_exception(self):
        url = 'test-url'
        message = Mock()
        channel = Mock()
        channel.acknowledge.side_effect = ValueError

        # test
        endpoint = Endpoint(url)
        endpoint._channel = channel
        self.assertRaises(ValueError, endpoint.ack, message)

    @patch('gofer.messaging.adapter.qpid.endpoint.RELEASED')
    @patch('gofer.messaging.adapter.qpid.endpoint.Disposition')
    def test_reject_released(self, disposition, released):
        url = 'test-url'
        message = Mock()

        # test
        endpoint = Endpoint(url)
        endpoint._channel = Mock()
        endpoint.reject(message)

        # validation
        disposition.assert_called_once_with(released)
        endpoint._channel.acknowledge.assert_called_once_with(
            message=message, disposition=disposition.return_value)

    @patch('gofer.messaging.adapter.qpid.endpoint.Disposition')
    def test_reject_exception(self, disposition):
        url = 'test-url'
        message = Mock()
        channel = Mock()
        channel.acknowledge.side_effect = ValueError

        # test
        endpoint = Endpoint(url)
        endpoint._channel = channel
        self.assertRaises(ValueError, endpoint.reject, message)


    @patch('gofer.messaging.adapter.qpid.endpoint.REJECTED')
    @patch('gofer.messaging.adapter.qpid.endpoint.Disposition')
    def test_reject_rejected(self, disposition, rejected):
        url = 'test-url'
        message = Mock()

        # test
        endpoint = Endpoint(url)
        endpoint._channel = Mock()
        endpoint.reject(message, requeue=False)

        # validation
        disposition.assert_called_once_with(rejected)
        endpoint._channel.acknowledge.assert_called_once_with(
            message=message, disposition=disposition.return_value)

    @patch('gofer.messaging.adapter.qpid.endpoint.Connection')
    def test_open(self, connection):
        endpoint = Endpoint('')

        # test
        endpoint.open()

        # validation
        connection.assert_called_once_with(endpoint.url)
        connection.return_value.open.assert_called_once_with()
        self.assertEqual(endpoint._connection, connection.return_value)
        self.assertEqual(endpoint._channel, connection.return_value.channel.return_value)

    @patch('gofer.messaging.adapter.qpid.endpoint.Connection')
    def test_open_already(self, connection):
        endpoint = Endpoint('')

        # test
        endpoint.is_open = Mock(return_value=True)
        endpoint.open()

        # validation
        self.assertFalse(connection.called)

    def test_close(self):
        endpoint = Endpoint('')
        # soft
        channel = Mock()
        connection = Mock()
        endpoint._channel = channel
        endpoint._connection = connection
        endpoint.close()
        channel.close.assert_called_once_with()
        connection.close.assert_called_once_with(False)
        self.assertEqual(endpoint._channel, None)
        self.assertEqual(endpoint._connection, None)
        # hard
        channel = Mock()
        connection = Mock()
        endpoint._channel = channel
        endpoint._connection = connection
        endpoint.close(True)
        channel.close.assert_called_once_with()
        connection.close.assert_called_once_with(True)
        self.assertEqual(endpoint._channel, None)
        self.assertEqual(endpoint._connection, None)
        # not open
        channel = Mock()
        connection = Mock()
        endpoint._channel = channel
        endpoint._connection = connection
        endpoint.is_open = Mock(return_value=False)
        endpoint.close()
        self.assertFalse(channel.close.called)
        self.assertFalse(connection.close.called)

    def test_close_channel(self):
        channel = Mock()

         # test
        endpoint = Endpoint('')
        endpoint._channel = channel
        endpoint._close_channel()

        # validation
        channel.close.assert_called_once_with()

    def test_close_channel_exception(self):
        channel = Mock()
        channel.close.side_effect = ValueError

         # test
        endpoint = Endpoint('')
        endpoint._channel = channel
        endpoint._close_channel()

        # validation
        channel.close.assert_called_once_with()
