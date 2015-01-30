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
    from gofer.messaging.adapter.amqp.consumer import NotFound, opener
    from gofer.messaging.adapter.amqp.consumer import Receiver, Inbox, Empty
    from gofer.messaging.adapter.amqp.consumer import Reader, BaseReader
    from gofer.messaging.adapter.amqp.consumer import DELIVERY_TAG


class Queue(object):

    def __init__(self, name):
        self.name = name


class Thing(object):

    @opener
    def open(self, exception=None):
        if exception:
            raise exception


class ChannelError(Exception):

    def __init__(self, code):
        self.code = code


class TestOpener(TestCase):

    @patch('gofer.messaging.adapter.amqp.consumer.ChannelError', ChannelError)
    def test_call(self):
        t = Thing()
        t.open()
        # 404
        self.assertRaises(NotFound, t.open, ChannelError(404))
        # other
        self.assertRaises(ChannelError, t.open, ChannelError(500))


class TestReader(TestCase):

    @patch('gofer.messaging.adapter.amqp.consumer.Connection')
    def test_init(self, connection):
        queue = Mock()
        url = 'test-url'

        # test
        reader = Reader(queue, url=url)

        # validation
        connection.assert_called_once_with(url)
        self.assertTrue(isinstance(reader, BaseReader))
        self.assertEqual(reader.url, url)
        self.assertEqual(reader.connection, connection.return_value)
        self.assertEqual(reader.queue, queue)
        self.assertEqual(reader.channel, None)
        self.assertEqual(reader.receiver, None)

    @patch('gofer.messaging.adapter.amqp.consumer.Connection', Mock())
    def test_is_open(self):
        url = 'test-url'
        reader = Reader(Mock(), url=url)
        # closed
        self.assertFalse(reader.is_open())
        # open
        reader.receiver = Mock()
        self.assertTrue(reader.is_open())

    @patch('gofer.messaging.adapter.amqp.consumer.Connection')
    @patch('gofer.messaging.adapter.amqp.consumer.Receiver')
    def test_open(self, receiver, connection):
        url = 'test-url'
        queue = Queue('test-queue')
        receiver.return_value.open.return_value = receiver.return_value

        # test
        reader = Reader(queue, url)
        reader.is_open = Mock(return_value=False)
        reader.open()

        # validation
        connection.return_value.open.assert_called_once_with()
        connection.return_value.channel.assert_called_once_with()
        receiver.assert_called_once_with(reader)
        self.assertEqual(reader.channel, connection.return_value.channel.return_value)
        self.assertEqual(reader.receiver, receiver.return_value)

    @patch('gofer.messaging.adapter.amqp.consumer.Connection', Mock())
    @patch('gofer.messaging.adapter.amqp.consumer.Receiver')
    def test_open_already(self, receiver):
        url = 'test-url'
        queue = Mock(name='test-queue')

        # test
        reader = Reader(queue, url)
        reader.is_open = Mock(return_value=True)
        reader.open()

        # validation
        self.assertFalse(reader.connection.open.called)
        self.assertFalse(receiver.called)

    def test_close(self):
        connection = Mock()
        channel = Mock()
        receiver = Mock()

        # test
        reader = Reader(None)
        reader.connection = connection
        reader.channel = channel
        reader.receiver = receiver
        reader.is_open = Mock(return_value=True)
        reader.close()

        # validation
        receiver.close.assert_called_once_with()
        channel.close.assert_called_once_with()
        self.assertFalse(connection.close.called)

    def test_get(self):
        queue = Mock(name='test-queue')
        received = Mock(content='<body/>')
        url = 'test-url'

        # test
        reader = Reader(queue, url=url)
        reader.receiver = Mock()
        reader.receiver.fetch.return_value = received
        message = reader.get(10)

        # validation
        reader.receiver.fetch.assert_called_once_with(10)
        self.assertTrue(isinstance(message, Message))
        self.assertEqual(message._reader, reader)
        self.assertEqual(message._impl, received)
        self.assertEqual(message._body, received.body)

    def test_ack(self):
        url = 'test-url'
        tag = '1234'
        queue = Mock()
        message = Mock(delivery_info={DELIVERY_TAG: tag})

        # test
        reader = Reader(queue, url=url)
        reader.channel = Mock()
        reader.ack(message)

        # validation
        reader.channel.basic_ack.assert_called_once_with(tag)

    def test_ack_exception(self):
        url = 'test-url'
        tag = '1234'
        queue = Mock()
        message = Mock(delivery_info={DELIVERY_TAG: tag})

        # test
        reader = Reader(queue, url=url)
        reader.channel = Mock()
        reader.channel.basic_ack.side_effect = ValueError

        # validation
        self.assertRaises(ValueError, reader.ack, message)

    def test_reject_requeue(self):
        url = 'test-url'
        tag = '1234'
        queue = Mock()
        message = Mock(delivery_info={DELIVERY_TAG: tag})

        # test
        reader = Reader(queue, url=url)
        reader.channel = Mock()
        reader.reject(message, True)

        # validation
        reader.channel.basic_reject.assert_called_once_with(tag, True)

    def test_reject_exception(self):
        url = 'test-url'
        tag = '1234'
        queue = Mock()
        message = Mock(delivery_info={DELIVERY_TAG: tag})

        # test
        reader = Reader(queue, url=url)
        reader.channel = Mock()
        reader.channel.basic_reject.side_effect = ValueError

        # validation
        self.assertRaises(ValueError, reader.reject, message)

    def test_reject_discarded(self):
        url = 'test-url'
        tag = '1234'
        queue = Mock()
        message = Mock(delivery_info={DELIVERY_TAG: tag})

        # test
        reader = Reader(queue, url=url)
        reader.channel = Mock()
        reader.reject(message, False)

        # validation
        reader.channel.basic_reject.assert_called_once_with(tag, False)

    @patch('gofer.messaging.adapter.amqp.consumer.Empty', Empty)
    def test_get_empty(self):
        queue = Mock(name='test-queue')
        url = 'test-url'

        # test
        reader = Reader(queue, url=url)
        reader.receiver = Mock()
        reader.receiver.fetch.side_effect = Empty
        message = reader.get(10)

        # validation
        reader.receiver.fetch.assert_called_once_with(10)
        self.assertEqual(message, None)


class TestReceiver(TestCase):

    @patch('select.epoll')
    def test_wait(self, epoll):
        fd = 0
        channel = Mock(method_queue=[])
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
    def test_wait(self, epoll):
        fd = 0
        channel = Mock(method_queue=[Mock()])
        timeout = 10

        epoll.return_value.poll.return_value = [fd]

        # test
        Receiver._wait(fd, channel, timeout)

        # validation
        self.assertFalse(epoll.called)
        channel.wait.assert_called_once_with()

    @patch('select.epoll')
    def test_wait_nothing(self, epoll):
        fd = 0
        channel = Mock(method_queue=[])
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
        reader = Mock(channel=Mock())
        r = Receiver(reader)
        channel = r.channel()
        self.assertEqual(channel, reader.channel)

    def test_open(self):
        queue = Mock()
        reader = Mock(queue=queue, channel=Mock())

        # test
        r = Receiver(reader)
        r = r.open()

        # validation
        reader.channel.basic_consume.assert_called_once_with(queue.name, callback=r.inbox.put)
        self.assertEqual(r.tag, reader.channel.basic_consume.return_value)

    def test_close(self):
        reader = Mock(channel=Mock())
        tag = 1234

        # test
        r = Receiver(reader)
        r.tag = tag
        r.close()

        # validation
        reader.channel.basic_cancel.assert_called_once_with(tag)

    def test_close_exception(self):
        reader = Mock()
        reader.channel.basic_cancel.side_effect = ValueError
        tag = 1234

        # test
        r = Receiver(reader)
        r.tag = tag
        r.close()

        # validation
        reader.channel.basic_cancel.assert_called_once_with(tag)

    def test_fetch(self):
        timeout = 10
        channel = Mock()
        reader = Mock(channel=channel)
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
        reader = Mock(channel=channel)

        # test
        r = Receiver(reader)
        r.inbox = Mock()
        r.inbox.empty.return_value = False
        r.inbox.get.side_effect = Empty
        r._wait = Mock(side_effect=r.inbox.put)
        self.assertRaises(r.fetch)
