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

with ipatch('qpid.messaging'):
    from gofer.messaging.adapter.qpid.consumer import subject
    from gofer.messaging.adapter.qpid.consumer import Reader, BaseReader


class TestSubject(TestCase):

    def test_subject(self):
        hello = 'hello'
        message = Mock(properties={'qpid.subject': hello})
        self.assertEqual(subject(message), hello)


class Empty(Exception):
    pass


class TestReader(TestCase):

    @patch('gofer.messaging.adapter.qpid.consumer.Endpoint')
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

    @patch('gofer.messaging.adapter.qpid.consumer.Endpoint', Mock())
    def test_endpoint(self):
        reader = Reader(None)
        returned = reader.endpoint()
        self.assertEqual(returned, reader._endpoint)

    @patch('gofer.messaging.adapter.qpid.consumer.Endpoint', Mock())
    @patch('gofer.messaging.adapter.qpid.consumer.BaseReader.open')
    def test_open(self, _open):
        queue = Mock(name='test-queue')
        channel = Mock()

        # test
        reader = Reader(queue)
        reader.channel = Mock(return_value=channel)
        reader.is_open = Mock(return_value=False)
        reader.open()

        # validation
        _open.assert_called_once_with(reader)
        channel.receiver.assert_called_once_with(queue.name)
        self.assertEqual(reader._receiver, channel.receiver.return_value)
        
    @patch('gofer.messaging.adapter.qpid.consumer.Endpoint', Mock())
    @patch('gofer.messaging.adapter.qpid.consumer.BaseReader.open')
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
        self.assertEqual(message._body, received.content)

    @patch('gofer.messaging.adapter.qpid.consumer.Empty', Empty)
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

    @patch('gofer.messaging.adapter.qpid.consumer.sleep')
    @patch('gofer.messaging.adapter.qpid.consumer.Empty', Empty)
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

    @patch('gofer.messaging.adapter.qpid.consumer.Endpoint', Mock())
    @patch('gofer.messaging.adapter.qpid.consumer.BaseReader.close')
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

    @patch('gofer.messaging.adapter.qpid.consumer.Endpoint', Mock())
    @patch('gofer.messaging.adapter.qpid.consumer.BaseReader.close')
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
