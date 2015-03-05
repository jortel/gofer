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
#
# Jeff Ortel <jortel@redhat.com>
#

from unittest import TestCase

from mock import Mock, patch

from gofer.devel import ipatch

from gofer.messaging.adapter.model import NotFound

with ipatch('amqp'):
    from gofer.messaging.adapter.amqp.reliability import reliable, DELAY
    from gofer.messaging.adapter.amqp.reliability import Endpoint, endpoint


class ConnectionException(Exception):
    pass


class ChannelError(Exception):

    def __init__(self, code=0):
        self.code = code


class TestReliable(TestCase):

    def test_reliable(self):
        fn = Mock()
        messenger = Mock()
        args = (messenger, 2, 3)
        kwargs = {'A': 1}

        # test
        wrapped = reliable(fn)
        wrapped(*args, **kwargs)

        # validation
        fn.assert_called_once_with(*args, **kwargs)

    @patch('gofer.messaging.adapter.amqp.reliability.CONNECTION_EXCEPTIONS', ConnectionException)
    @patch('gofer.messaging.adapter.amqp.reliability.sleep')
    def test_reliable_connection_exception(self, sleep):
        url = 'test-url'
        fn = Mock(side_effect=[ConnectionException, None])
        messenger = Mock(url=url, connection=Mock())
        args = (messenger, 2, 3)
        kwargs = {'A': 1}

        # test
        wrapped = reliable(fn)
        wrapped(*args, **kwargs)

        # validation
        sleep.assert_called_once_with(DELAY)
        messenger.repair.assert_called_once_with()
        self.assertEqual(
            fn.call_args_list,
            [
                (args, kwargs),
                (args, kwargs),
            ])

    @patch('gofer.messaging.adapter.amqp.reliability.ChannelError', ChannelError)
    @patch('gofer.messaging.adapter.amqp.reliability.sleep')
    def test_reliable_channel_exception(self, sleep):
        url = 'test-url'
        fn = Mock(side_effect=[ChannelError, None])
        messenger = Mock(url=url, connection=Mock())
        args = (messenger, 2, 3)
        kwargs = {'A': 1}

        # test
        wrapped = reliable(fn)
        wrapped(*args, **kwargs)

        # validation
        sleep.assert_called_once_with(DELAY)
        messenger.repair.assert_called_once_with()
        self.assertEqual(
            fn.call_args_list,
            [
                (args, kwargs),
                (args, kwargs),
            ])

    @patch('gofer.messaging.adapter.amqp.reliability.ChannelError', ChannelError)
    @patch('gofer.messaging.adapter.amqp.reliability.sleep')
    def test_reliable_channel_exception_not_found(self, sleep):
        url = 'test-url'
        fn = Mock(side_effect=[ChannelError(404), None])
        messenger = Mock(url=url, connection=Mock())
        args = (messenger, 2, 3)
        kwargs = {'A': 1}

        # test
        wrapped = reliable(fn)

        # validation
        self.assertRaises(NotFound, wrapped, *args, **kwargs)
        self.assertFalse(sleep.called)

    @patch('gofer.messaging.adapter.amqp.reliability.Endpoint')
    def test_endpoint(self, messenger):
        fn = Mock()
        url = Mock()
        args = (messenger.return_value,)

        # test
        wrapped = endpoint(fn)
        wrapped(url)

        # validation
        messenger.assert_called_once_with(url)
        messenger.return_value.open.assert_called_once_with()
        fn.assert_called_once_with(*args)
        messenger.return_value.close.assert_called_once_with()


class TestEndpoint(TestCase):

    @patch('gofer.messaging.adapter.amqp.reliability.Connection')
    def test_init(self, connection):
        url = Mock()
        messenger = Endpoint(url)
        connection.assert_called_once_with(url)
        self.assertEqual(messenger.connection, connection.return_value)
        self.assertEqual(messenger.channel, None)

    @patch('gofer.messaging.adapter.amqp.reliability.Connection', Mock())
    def test_open(self):
        url = Mock()
        messenger = Endpoint(url)
        messenger.open()
        messenger.connection.open.assert_called_once_with()
        self.assertEqual(messenger.channel, messenger.connection.channel.return_value)
        
    @patch('gofer.messaging.adapter.amqp.reliability.Connection', Mock())
    def test_repair(self):
        url = Mock()
        messenger = Endpoint(url)
        messenger.repair()
        messenger.connection.close.assert_called_once_with()
        messenger.connection.open.assert_called_once_with()
        self.assertEqual(messenger.channel, messenger.connection.channel.return_value)

    @patch('gofer.messaging.adapter.amqp.reliability.Connection', Mock())
    def test_close(self):
        url = Mock()
        messenger = Endpoint(url)
        messenger.connection = Mock()
        messenger.channel = Mock()
        messenger.close()
        messenger.channel.close.assert_called_once_with()

    @patch('gofer.messaging.adapter.amqp.reliability.Connection', Mock())
    def test_close_failed(self):
        url = Mock()
        messenger = Endpoint(url)
        messenger.connection = Mock()
        messenger.channel = Mock()
        messenger.channel.close.side_effect = ValueError
        messenger.close()
        messenger.channel.close.assert_called_once_with()
