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

with ipatch('amqp'):
    from gofer.messaging.adapter.amqp.endpoint import Endpoint, BaseEndpoint
    from gofer.messaging.adapter.amqp.endpoint import DELIVERY_TAG, CONNECTION_EXCEPTIONS
    from gofer.messaging.adapter.amqp.endpoint import reliable, endpoint as endpoint_decorator


class TestDecorators(TestCase):

    def test_reliable(self):
        fn = Mock()
        endpoint = Mock()
        args = (endpoint, 2, 3)
        kwargs = {'A': 1}

        # test
        wrapped = reliable(fn)
        wrapped(*args, **kwargs)

        # validation
        fn.assert_called_once_with(*args, **kwargs)

    @patch('gofer.messaging.adapter.amqp.endpoint.sleep')
    def test_reliable_with_errors(self, sleep):
        url = 'test-url'
        fn = Mock(side_effect=[CONNECTION_EXCEPTIONS[0], 'okay'])
        endpoint = Mock(url=url)
        args = (endpoint, 2, 3)
        kwargs = {'A': 1}

        # test
        wrapped = reliable(fn)
        wrapped(*args, **kwargs)

        # validation
        endpoint.close.assert_called_once_with(hard=True)
        sleep.assert_called_once_with(3)
        endpoint.open.assert_called_once_with()
        self.assertEqual(
            fn.call_args_list,
            [
                (args, kwargs),
                (args, kwargs),
            ])

    @patch('gofer.messaging.adapter.amqp.endpoint.Endpoint')
    def test_endpoint(self, endpoint):
        fn = Mock()
        url = Mock()
        args = (endpoint.return_value,)

        # test
        wrapped = endpoint_decorator(fn)
        wrapped(url)

        # validation
        endpoint.assert_called_once_with(url)
        fn.assert_called_once_with(*args)


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
        tag = '1234'
        message = Mock(delivery_info={DELIVERY_TAG: tag})

        # test
        endpoint = Endpoint(url)
        endpoint._channel = Mock()
        endpoint.ack(message)

        # validation
        endpoint._channel.basic_ack.assert_called_once_with(tag)

    def test_ack_exception(self):
        url = 'test-url'
        tag = '1234'
        message = Mock(delivery_info={DELIVERY_TAG: tag})
        channel = Mock()
        channel.basic_ack.side_effect = ValueError

        # test
        endpoint = Endpoint(url)
        endpoint._channel = channel
        self.assertRaises(ValueError, endpoint.ack, message)

    def test_reject_requeue(self):
        url = 'test-url'
        tag = '1234'
        message = Mock(delivery_info={DELIVERY_TAG: tag})

        # test
        endpoint = Endpoint(url)
        endpoint._channel = Mock()
        endpoint.reject(message, True)

        # validation
        endpoint._channel.basic_reject.assert_called_once_with(tag, True)

    def test_reject_exception(self):
        url = 'test-url'
        tag = '1234'
        message = Mock(delivery_info={DELIVERY_TAG: tag})

        # test
        endpoint = Endpoint(url)
        endpoint._channel = Mock()
        endpoint._channel.basic_reject.side_effect = ValueError
        self.assertRaises(ValueError, endpoint.reject, message, True)

    def test_reject_discarded(self):
        url = 'test-url'
        tag = '1234'
        message = Mock(delivery_info={DELIVERY_TAG: tag})

        # test
        endpoint = Endpoint(url)
        endpoint._channel = Mock()
        endpoint.reject(message, False)

        # validation
        endpoint._channel.basic_reject.assert_called_once_with(tag, False)

    @patch('gofer.messaging.adapter.amqp.endpoint.Connection')
    def test_open(self, connection):
        endpoint = Endpoint('')

        # test
        endpoint.open()

        # validation
        connection.assert_called_once_with(endpoint.url)
        connection.return_value.open.assert_called_once_with()
        self.assertEqual(endpoint._connection, connection.return_value)
        self.assertEqual(endpoint._channel, connection.return_value.channel.return_value)

    @patch('gofer.messaging.adapter.amqp.endpoint.Connection')
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

    def test_close_exception(self):
        channel = Mock()
        channel.close.side_effect = CONNECTION_EXCEPTIONS[0]

         # test
        endpoint = Endpoint('')
        endpoint._channel = channel
        endpoint._connection = Mock()
        endpoint.close()

        # validation
        channel.close.assert_called_once_with()
