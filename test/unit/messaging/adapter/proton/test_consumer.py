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

from gofer.messaging.adapter.model import Message

with ipatch('proton'):
    from gofer.messaging.adapter.proton.consumer import Reader, BaseReader


class Timeout(Exception):
    pass


class Queue(object):

    def __init__(self, name):
        self.name = name


class LinkException(Exception):
    pass


class TestReader(TestCase):

    @patch('gofer.messaging.adapter.proton.consumer.Connection')
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
        self.assertEqual(reader.receiver, None)

    @patch('gofer.messaging.adapter.proton.consumer.Connection', Mock())
    def test_is_open(self):
        url = 'test-url'
        reader = Reader(Mock(), url=url)
        # closed
        self.assertFalse(reader.is_open())
        # open
        reader.receiver = Mock()
        self.assertTrue(reader.is_open())

    @patch('gofer.messaging.adapter.proton.consumer.Connection')
    def test_open(self, connection):
        url = 'test-url'
        queue = Queue('test-queue')

        # test
        reader = Reader(queue, url)
        reader.is_open = Mock(return_value=False)
        reader.open()

        # validation
        connection.return_value.open.assert_called_once_with()
        connection.return_value.receiver.assert_called_once_with(queue.name)
        self.assertEqual(reader.receiver, reader.connection.receiver.return_value)

    @patch('gofer.messaging.adapter.proton.consumer.Connection', Mock())
    def test_open_already(self):
        url = 'test-url'
        queue = Queue('test-queue')

        # test
        reader = Reader(queue, url)
        reader.is_open = Mock(return_value=True)
        reader.open()

        # validation
        self.assertFalse(reader.connection.open.called)

    def test_close(self):
        connection = Mock()
        receiver = Mock()
        receiver.close.side_effect = KeyError

        # test
        reader = Reader(None, '')
        reader.connection = connection
        reader.receiver = receiver
        reader.is_open = Mock(return_value=True)
        reader.close()

        # validation
        receiver.close.assert_called_once_with()
        self.assertFalse(connection.close.called)

    def test_get(self):
        queue = Queue('test-queue')
        received = Mock(body='<body/>')
        url = 'test-url'

        # test
        reader = Reader(queue, url=url)
        reader.receiver = Mock()
        reader.receiver.receive.return_value = received
        message = reader.get(10)

        # validation
        reader.receiver.receive.assert_called_once_with(10)
        self.assertTrue(isinstance(message, Message))
        self.assertEqual(message._reader, reader)
        self.assertEqual(message._impl, received)
        self.assertEqual(message._body, received.body)

    @patch('gofer.messaging.adapter.proton.consumer.Timeout', Timeout)
    def test_get_empty(self):
        queue = Mock(name='test-queue')
        url = 'test-url'

        # test
        reader = Reader(queue, url=url)
        reader.receiver = Mock()
        reader.receiver.receive.side_effect = Timeout
        message = reader.get(10)

        # validation
        reader.receiver.receive.assert_called_once_with(10)
        self.assertEqual(message, None)

    def test_ack(self):
        queue = Mock(name='test-queue')
        url = 'test-url'

        # test
        reader = Reader(queue, url=url)
        reader.receiver = Mock()
        reader.ack(None)

        # validation
        reader.receiver.accept.assert_called_once_with()

    def test_reject(self):
        queue = Mock(name='test-queue')
        url = 'test-url'

        # test
        reader = Reader(queue, url=url)
        reader.receiver = Mock()
        reader.reject(None, requeue=False)

        # validation
        reader.receiver.reject.assert_called_once_with()

    def test_reject_queued(self):
        queue = Mock(name='test-queue')
        url = 'test-url'

        # test
        reader = Reader(queue, url=url)
        reader.receiver = Mock()
        reader.reject(None, requeue=True)

        # validation
        reader.receiver.release.assert_called_once_with()
