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

with ipatch('amqplib'):
    from gofer.messaging.adapter.amqplib.endpoint import Endpoint, BaseEndpoint
    from gofer.messaging.adapter.amqplib.endpoint import DELIVERY_TAG, CONNECTION_EXCEPTIONS
    from gofer.messaging.adapter.amqplib.endpoint import reliable, endpoint as endpoint_decorator


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

    @patch('gofer.messaging.adapter.amqplib.endpoint.sleep')
    @patch('gofer.messaging.adapter.amqplib.endpoint.Broker')
    def test_reliable_with_errors(self, broker, sleep):
        url = 'test-url'
        fn = Mock(side_effect=[CONNECTION_EXCEPTIONS[0], 'okay'])
        endpoint = Mock(url=url)
        args = (endpoint, 2, 3)
        kwargs = {'A': 1}

        # test
        wrapped = reliable(fn)
        wrapped(*args, **kwargs)

        # validation
        broker.assert_called_any_with(endpoint.url)
        endpoint.close.assert_called_once_with()
        broker.return_value.close.assert_called_once_with()
        sleep.assert_called_once_with(3)
        endpoint.channel.assert_called_once_with()
        self.assertEqual(
            fn.call_args_list,
            [
                (args, kwargs),
                (args, kwargs),
            ])

    @patch('gofer.messaging.adapter.amqplib.endpoint.Endpoint')
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

    @patch('gofer.messaging.adapter.amqplib.endpoint.RLock')
    def test_init(self, rlock):
        url = 'test-url'

        # test
        endpoint = Endpoint(url)

        # validation
        self.assertTrue(isinstance(endpoint, BaseEndpoint))
        self.assertEqual(endpoint._Endpoint__mutex, rlock.return_value)
        self.assertEqual(endpoint._Endpoint__channel, None)
        self.assertEqual(endpoint.url, url)

    @patch('gofer.messaging.adapter.amqplib.endpoint.Broker')
    @patch('gofer.messaging.adapter.amqplib.endpoint.RLock', Mock())
    def test_channel(self, broker):
        url = 'test-url'
        connection = Mock()
        broker.return_value.connect.return_value = connection

        # test
        endpoint = Endpoint(url)
        channel = endpoint.channel()

        # validation
        broker.assert_called_once_with(url)
        connection.channel.assert_called_once_with()
        endpoint._Endpoint__mutex.lock.acquire.asssert_called_once_with()
        endpoint._Endpoint__mutex.lock.release.asssert_called_once_with()
        self.assertEqual(channel, connection.channel.return_value)
        self.assertEqual(channel, endpoint._Endpoint__channel)

    @patch('gofer.messaging.adapter.amqplib.endpoint.Broker')
    @patch('gofer.messaging.adapter.amqplib.endpoint.RLock', Mock())
    def test_channel_cached(self, broker):
        url = 'test-url'

        # test
        endpoint = Endpoint(url)
        endpoint._Endpoint__channel = Mock()
        channel = endpoint.channel()

        # validation
        endpoint._Endpoint__mutex.lock.acquire.asssert_called_once_with()
        endpoint._Endpoint__mutex.lock.release.asssert_called_once_with()
        self.assertEqual(channel, endpoint._Endpoint__channel)
        self.assertFalse(broker.called)

    @patch('gofer.messaging.adapter.amqplib.endpoint.RLock', Mock())
    def test_ack(self):
        url = 'test-url'
        tag = '1234'
        message = Mock(delivery_info={DELIVERY_TAG: tag})

        # test
        endpoint = Endpoint(url)
        endpoint._Endpoint__channel = Mock()
        endpoint.ack(message)

        # validation
        endpoint._Endpoint__channel.basic_ack.assert_called_once_with(tag)

    @patch('gofer.messaging.adapter.amqplib.endpoint.RLock', Mock())
    def test_ack_exception(self):
        url = 'test-url'
        tag = '1234'
        message = Mock(delivery_info={DELIVERY_TAG: tag})
        channel = Mock()
        channel.basic_ack.side_effect = ValueError

        # test
        endpoint = Endpoint(url)
        endpoint._Endpoint__channel = channel
        self.assertRaises(ValueError, endpoint.ack, message)

    @patch('gofer.messaging.adapter.amqplib.endpoint.RLock', Mock())
    def test_reject_requeue(self):
        url = 'test-url'
        tag = '1234'
        message = Mock(delivery_info={DELIVERY_TAG: tag})

        # test
        endpoint = Endpoint(url)
        endpoint._Endpoint__channel = Mock()
        endpoint.reject(message, True)

        # validation
        endpoint._Endpoint__channel.basic_reject.assert_called_once_with(tag, True)

    @patch('gofer.messaging.adapter.amqplib.endpoint.RLock', Mock())
    def test_reject_exception(self):
        url = 'test-url'
        tag = '1234'
        message = Mock(delivery_info={DELIVERY_TAG: tag})

        # test
        endpoint = Endpoint(url)
        endpoint._Endpoint__channel = Mock()
        endpoint._Endpoint__channel.basic_reject.side_effect = ValueError
        self.assertRaises(ValueError, endpoint.reject, message, True)

    @patch('gofer.messaging.adapter.amqplib.endpoint.RLock', Mock())
    def test_reject_discarded(self):
        url = 'test-url'
        tag = '1234'
        message = Mock(delivery_info={DELIVERY_TAG: tag})

        # test
        endpoint = Endpoint(url)
        endpoint._Endpoint__channel = Mock()
        endpoint.reject(message, False)

        # validation
        endpoint._Endpoint__channel.basic_reject.assert_called_once_with(tag, False)

    @patch('gofer.messaging.adapter.amqplib.endpoint.RLock', Mock())
    def test_open(self):
        endpoint = Endpoint('')
        endpoint.open()

    @patch('gofer.messaging.adapter.amqplib.endpoint.RLock', Mock())
    def test_close(self):
        channel = Mock()

        # test
        endpoint = Endpoint('')
        endpoint._Endpoint__channel = channel
        endpoint.close()

        # validation
        endpoint._Endpoint__mutex.lock.acquire.asssert_called_once_with()
        endpoint._Endpoint__mutex.lock.release.asssert_called_once_with()
        channel.close.assert_called_once_with()
        self.assertEqual(endpoint._Endpoint__channel, None)

    @patch('gofer.messaging.adapter.amqplib.endpoint.RLock', Mock())
    def test_close_exception(self):
        channel = Mock()
        channel.close.side_effect = CONNECTION_EXCEPTIONS[0]

         # test
        endpoint = Endpoint('')
        endpoint._Endpoint__channel = channel
        endpoint.close()

        # validation
        endpoint._Endpoint__mutex.lock.acquire.asssert_called_once_with()
        endpoint._Endpoint__mutex.lock.release.asssert_called_once_with()
        channel.close.assert_called_once_with()
        self.assertEqual(endpoint._Endpoint__channel, None)

    @patch('gofer.messaging.adapter.amqplib.endpoint.RLock', Mock())
    def test_close_no_channel(self):
        channel = Mock()

        # test
        endpoint = Endpoint('')
        endpoint.close()

        # validation
        endpoint._Endpoint__mutex.lock.acquire.asssert_called_once_with()
        endpoint._Endpoint__mutex.lock.release.asssert_called_once_with()
        self.assertFalse(channel.close.called)

    @patch('gofer.messaging.adapter.amqplib.endpoint.RLock', Mock())
    def test_del(self):
        endpoint = Endpoint('')
        endpoint.close = Mock()
        endpoint.__del__()
        endpoint.close.assert_called_once_with()

    @patch('gofer.messaging.adapter.amqplib.endpoint.RLock', Mock())
    def test_del_exception(self):
        endpoint = Endpoint('')
        endpoint.close = Mock(side_effect=ValueError)
        endpoint.__del__()
        endpoint.close.assert_called_once_with()

    @patch('gofer.messaging.adapter.amqplib.endpoint.RLock', Mock())
    def test_enter(self):
        endpoint = Endpoint('')
        endpoint.open = Mock()
        obj = endpoint.__enter__()
        endpoint.open.assert_called_once_with()
        self.assertEqual(obj, endpoint)

    @patch('gofer.messaging.adapter.amqplib.endpoint.RLock', Mock())
    def test_exit(self):
        endpoint = Endpoint('')
        endpoint.close = Mock()
        endpoint.__exit__()
        endpoint.close.assert_called_once_with()
