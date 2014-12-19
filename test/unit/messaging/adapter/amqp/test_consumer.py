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

import select

from unittest import TestCase

from mock import Mock, patch

from gofer.devel import ipatch

from gofer.messaging.adapter.model import Message

with ipatch('amqp'):
    from gofer.messaging.adapter.amqp.consumer import Receiver, Inbox, Empty
    from gofer.messaging.adapter.amqp.consumer import Reader, BaseReader


class TestReader(TestCase):

    @patch('gofer.messaging.adapter.amqp.consumer.Endpoint')
    def test_init(self, endpoint):
        queue = Mock()
        url = 'test-url'

        # test
        reader = Reader(queue, url=url)

        # validation
        endpoint.assert_called_once_with(url)
        self.assertTrue(isinstance(reader, BaseReader))
        self.assertEqual(reader.url, url)
        self.assertEqual(reader.queue, queue)
        self.assertEqual(reader._receiver, None)
        self.assertEqual(reader._endpoint, endpoint.return_value)

    @patch('gofer.messaging.adapter.amqp.consumer.Endpoint', Mock())
    def test_endpoint(self):
        reader = Reader(None)
        returned = reader.endpoint()
        self.assertEqual(returned, reader._endpoint)

    @patch('gofer.messaging.adapter.amqp.consumer.Endpoint', Mock())
    @patch('gofer.messaging.adapter.amqp.consumer.Receiver')
    @patch('gofer.messaging.adapter.amqp.consumer.BaseReader.open')
    def test_open(self, _open, receiver):
        queue = Mock(name='test-queue')
        channel = Mock()

        # test
        reader = Reader(queue)
        reader.channel = Mock(return_value=channel)
        reader.is_open = Mock(return_value=False)
        reader.open()

        # validation
        _open.assert_called_once_with(reader)
        receiver.assert_called_once_with(reader)
        self.assertEqual(reader._receiver, receiver.return_value)
        
    @patch('gofer.messaging.adapter.amqp.consumer.Endpoint', Mock())
    @patch('gofer.messaging.adapter.amqp.consumer.BaseReader.open')
    def test_open_already(self, _open):
        queue = Mock(name='test-queue')
        channel = Mock()

        # test
        reader = Reader(queue)
        reader.channel = Mock(return_value=channel)
        reader.is_open = Mock(return_value=True)
        reader.open()

        # validation
        self.assertFalse(_open.called)
        self.assertFalse(channel.receiver.called)

    def test_get(self):
        queue = Mock(name='test-queue')
        received = Mock(content='<body/>')
        url = 'test-url'

        # test
        reader = Reader(queue, url=url)
        reader._receiver = Mock()
        reader._receiver.fetch.return_value = received
        message = reader.get(10)

        # validation
        reader._receiver.fetch.assert_called_once_with(10)
        self.assertTrue(isinstance(message, Message))
        self.assertEqual(message._reader, reader)
        self.assertEqual(message._impl, received)
        self.assertEqual(message._body, received.body)

    @patch('gofer.messaging.adapter.amqp.consumer.Empty', Empty)
    def test_get_empty(self):
        queue = Mock(name='test-queue')
        url = 'test-url'

        # test
        reader = Reader(queue, url=url)
        reader._receiver = Mock()
        reader._receiver.fetch.side_effect = Empty
        message = reader.get(10)

        # validation
        reader._receiver.fetch.assert_called_once_with(10)
        self.assertEqual(message, None)

    @patch('gofer.messaging.adapter.amqp.consumer.sleep')
    @patch('gofer.messaging.adapter.amqp.consumer.Empty', Empty)
    def test_get_raised(self, sleep):
        queue = Mock(name='test-queue')
        url = 'test-url'

        # test
        reader = Reader(queue, url=url)
        reader._receiver = Mock()
        reader._receiver.fetch.side_effect = ValueError
        message = reader.get(10)

        # validation
        reader._receiver.fetch.assert_called_once_with(10)
        sleep.assert_called_once_with(60)
        self.assertEqual(message, None)

    @patch('gofer.messaging.adapter.amqp.consumer.Endpoint', Mock())
    @patch('gofer.messaging.adapter.amqp.consumer.BaseReader.close')
    def test_close(self, close):
        receiver = Mock()

        # test
        reader = Reader(None)
        reader._receiver = receiver
        reader.is_open = Mock(return_value=True)
        reader.close()

        # validation
        receiver.close.assert_called_once_with()
        close.assert_called_once_with(reader, False)

    @patch('gofer.messaging.adapter.amqp.consumer.Endpoint', Mock())
    @patch('gofer.messaging.adapter.amqp.consumer.BaseReader.close')
    def test_close_not_open(self, close):
        receiver = Mock()

        # test
        reader = Reader(None)
        reader._receiver = receiver
        reader.is_open = Mock(return_value=False)
        reader.close()

        # validation
        self.assertFalse(receiver.close.called)
        self.assertFalse(close.called)


class TestReceiver(TestCase):

    @patch('select.epoll')
    def test_wait(self, epoll):
        fd = 0
        channel = Mock()
        timeout = 10

        epoll.return_value.poll.return_value = [fd]

        # test
        Receiver._wait(fd, channel, timeout)

        # validation
        epoll.assert_called_once_with()
        epoll.return_value.register.assert_called_with(fd, select.EPOLLIN)
        epoll.return_value.poll.assert_called_with(timeout)
        channel.wait.assert_called_once_with()

    @patch('select.epoll')
    def test_wait_nothing(self, epoll):
        fd = 0
        channel = Mock()
        timeout = 10

        epoll.return_value.poll.return_value = []

        # test
        Receiver._wait(fd, channel, timeout)

        # validation
        epoll.assert_called_once_with()
        epoll.return_value.register.assert_called_with(fd, select.EPOLLIN)
        epoll.return_value.poll.assert_called_with(timeout)
        self.assertFalse(channel.wait.called)

    def test_init(self):
        reader = Mock()
        r = Receiver(reader)
        self.assertEqual(r.reader, reader)
        self.assertEqual(r.tag, None)
        self.assertTrue(isinstance(r.inbox, Inbox))

    def test_channel(self):
        reader = Mock()
        r = Receiver(reader)
        channel = r.channel()
        self.assertEqual(channel, reader.channel.return_value)

    def test_open(self):
        queue = Mock()
        channel = Mock()
        reader = Mock(queue=queue)
        reader.channel.return_value = channel

        # test
        r = Receiver(reader)
        r.open()

        # validation
        channel.basic_consume.assert_called_once_with(queue.name, callback=r.inbox.put)
        self.assertEqual(r.tag, channel.basic_consume.return_value)

    def test_close(self):
        channel = Mock()
        reader = Mock()
        reader.channel.return_value = channel
        tag = 1234

        # test
        r = Receiver(reader)
        r.tag = tag
        r.close()

        # validation
        channel.basic_cancel.assert_called_once_with(tag)

    def test_fetch(self):
        timeout = 10
        channel = Mock()
        reader = Mock()
        reader.channel.return_value = channel
        received = 33

        # test
        r = Receiver(reader)
        r.inbox = Mock()
        r.inbox.empty.return_value = True
        r.inbox.get.return_value = received
        r._wait = Mock(side_effect=r.inbox.put)
        message = r.fetch(timeout)

        # validation
        fd = channel.connection.sock.fileno.return_value
        r._wait.assert_called_once_with(fd, channel, timeout)
        self.assertEqual(message, received)

    def test_fetch_empty(self):
        channel = Mock()
        reader = Mock()
        reader.channel.return_value = channel

        # test
        r = Receiver(reader)
        r.inbox = Mock()
        r.inbox.empty.return_value = False
        r.inbox.get.side_effect = Empty
        r._wait = Mock(side_effect=r.inbox.put)
        self.assertRaises(r.fetch)
