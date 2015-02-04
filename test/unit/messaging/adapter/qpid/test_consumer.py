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

with ipatch('qpid'):
    from gofer.messaging.adapter.qpid.consumer import Reader, BaseReader


class Empty(Exception):
    pass


class Queue(object):

    def __init__(self, name):
        self.name = name


class TestReader(TestCase):

    @patch('gofer.messaging.adapter.qpid.consumer.Connection')
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
        self.assertEqual(reader.session, None)
        self.assertEqual(reader.receiver, None)

    @patch('gofer.messaging.adapter.qpid.consumer.Connection', Mock())
    def test_is_open(self):
        url = 'test-url'
        reader = Reader(Mock(), url=url)
        # closed
        self.assertFalse(reader.is_open())
        # open
        reader.receiver = Mock()
        self.assertTrue(reader.is_open())

    @patch('gofer.messaging.adapter.qpid.consumer.Connection')
    def test_open(self, connection):
        url = 'test-url'
        queue = Queue('test-queue')

        # test
        reader = Reader(queue, url)
        reader.is_open = Mock(return_value=False)
        reader.open()

        # validation
        connection.return_value.open.assert_called_once_with()
        connection.return_value.session.assert_called_once_with()
        connection.return_value.session.return_value.receiver.assert_called_once_with(queue.name)
        self.assertEqual(reader.session, connection.return_value.session.return_value)
        self.assertEqual(reader.receiver, reader.session.receiver.return_value)

    @patch('gofer.messaging.adapter.qpid.consumer.Connection', Mock())
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
        session = Mock()
        receiver = Mock()

        # test
        reader = Reader(None)
        reader.connection = connection
        reader.session = session
        reader.receiver = receiver
        reader.is_open = Mock(return_value=True)
        reader.close()

        # validation
        receiver.close.assert_called_once_with()
        session.close.assert_called_once_with()
        self.assertFalse(connection.close.called)
        
    def test_ack(self):
        message = Mock()

        # test
        reader = Reader(None)
        reader.session = Mock()
        reader.ack(message)

        # validation
        reader.session.acknowledge.assert_called_once_with(message=message)

    def test_ack_exception(self):
        message = Mock()
        session = Mock()
        session.acknowledge.side_effect = ValueError

        # test
        reader = Reader(None)
        reader.session = session
        self.assertRaises(ValueError, reader.ack, message)

    @patch('gofer.messaging.adapter.qpid.consumer.RELEASED')
    @patch('gofer.messaging.adapter.qpid.consumer.Disposition')
    def test_reject_released(self, disposition, released):
        message = Mock()

        # test
        reader = Reader(None)
        reader.session = Mock()
        reader.reject(message)

        # validation
        disposition.assert_called_once_with(released)
        reader.session.acknowledge.assert_called_once_with(
            message=message, disposition=disposition.return_value)

    @patch('gofer.messaging.adapter.qpid.consumer.Disposition')
    def test_reject_exception(self, disposition):
        message = Mock()
        session = Mock()
        session.acknowledge.side_effect = ValueError

        # test
        reader = Reader(None)
        reader.session = session
        self.assertRaises(ValueError, reader.reject, message)


    @patch('gofer.messaging.adapter.qpid.consumer.REJECTED')
    @patch('gofer.messaging.adapter.qpid.consumer.Disposition')
    def test_reject_rejected(self, disposition, rejected):
        message = Mock()

        # test
        reader = Reader(None)
        reader.session = Mock()
        reader.reject(message, False)

        # validation
        disposition.assert_called_once_with(rejected)
        reader.session.acknowledge.assert_called_once_with(
            message=message, disposition=disposition.return_value)

    def test_get(self):
        queue = Queue('test-queue')
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
        self.assertEqual(message._body, received.content)

    @patch('gofer.messaging.adapter.qpid.consumer.Empty', Empty)
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

    @patch('gofer.messaging.adapter.qpid.consumer.sleep')
    @patch('gofer.messaging.adapter.qpid.consumer.Empty', Empty)
    def test_get_raised(self, sleep):
        queue = Mock(name='test-queue')
        url = 'test-url'

        # test
        reader = Reader(queue, url=url)
        reader.receiver = Mock()
        reader.receiver.fetch.side_effect = ValueError
        message = reader.get(10)

        # validation
        reader.receiver.fetch.assert_called_once_with(10)
        sleep.assert_called_once_with(60)
        self.assertEqual(message, None)
