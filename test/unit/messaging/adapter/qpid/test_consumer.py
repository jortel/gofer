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

from gofer.messaging import InvalidDocument

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
    @patch('gofer.messaging.adapter.qpid.consumer.RLock')
    def test_init(self, rlock, endpoint):
        queue = Mock()
        url = 'test-url'

        # test
        reader = Reader(queue, url=url)

        # validation
        endpoint.assert_called_once_with(url)
        self.assertTrue(isinstance(reader, BaseReader))
        self.assertEqual(reader.url, url)
        self.assertEqual(reader.queue, queue)
        self.assertFalse(reader._Reader__opened)
        self.assertEqual(reader._Reader__receiver, None)
        self.assertEqual(reader._Reader__mutex, rlock.return_value)
        self.assertEqual(reader._endpoint, endpoint.return_value)

    @patch('gofer.messaging.adapter.qpid.consumer.Endpoint', Mock())
    @patch('gofer.messaging.adapter.qpid.consumer.RLock', Mock())
    def test_endpoint(self):
        reader = Reader(None)
        returned = reader.endpoint()
        self.assertEqual(returned, reader._endpoint)

    @patch('gofer.messaging.adapter.qpid.consumer.Endpoint', Mock())
    @patch('gofer.messaging.adapter.qpid.consumer.RLock', Mock())
    @patch('gofer.messaging.adapter.qpid.consumer.BaseReader.open')
    def test_open(self, open):
        queue = Mock(name='test-queue')
        session = Mock()

        # test
        reader = Reader(queue)
        reader.channel = Mock(return_value=session)
        reader.open()

        # validation
        open.assert_called_once_with(reader)
        session.receiver.assert_called_once_with(queue.name)
        self.assertTrue(reader._Reader__opened)
        self.assertEqual(reader._Reader__receiver, session.receiver.return_value)

    @patch('gofer.messaging.adapter.qpid.consumer.Endpoint', Mock())
    @patch('gofer.messaging.adapter.qpid.consumer.RLock', Mock())
    @patch('gofer.messaging.adapter.qpid.consumer.BaseReader.open')
    def test_open_already(self, open):
        queue = Mock(name='test-queue')
        session = Mock()

        # test
        reader = Reader(queue)
        reader.channel = Mock(return_value=session)
        reader._Reader__opened = True
        reader.open()

        # validation
        self.assertTrue(open.called)
        self.assertFalse(session.receiver.called)

    @patch('gofer.messaging.adapter.qpid.consumer.Endpoint', Mock())
    @patch('gofer.messaging.adapter.qpid.consumer.RLock', Mock())
    @patch('gofer.messaging.adapter.qpid.consumer.BaseReader.close')
    def test_close(self, close):
        receiver = Mock()

        # test
        reader = Reader(None)
        reader._Reader__opened = True
        reader._Reader__receiver = receiver
        reader.close()

        # validation
        receiver.close.assert_called_once_with()
        close.assert_called_once_with(reader)
        self.assertFalse(reader._Reader__opened)
        self.assertEqual(reader._Reader__receiver, None)

    @patch('gofer.messaging.adapter.qpid.consumer.Endpoint', Mock())
    @patch('gofer.messaging.adapter.qpid.consumer.RLock', Mock())
    @patch('gofer.messaging.adapter.qpid.consumer.BaseReader.close')
    def test_close_not_open(self, close):
        receiver = Mock()

        # test
        reader = Reader(None)
        reader._Reader__opened = False
        reader._Reader__receiver = receiver
        reader.close()

        # validation
        self.assertFalse(receiver.close.called)

    @patch('gofer.messaging.adapter.qpid.consumer.sleep')
    @patch('gofer.messaging.adapter.qpid.consumer.Endpoint', Mock())
    @patch('gofer.messaging.adapter.qpid.consumer.RLock', Mock())
    def test_get(self, sleep):
        msg = Mock()
        receiver = Mock()
        receiver.fetch.return_value = msg

        # test
        reader = Reader(None)
        reader._Reader__receiver = receiver
        reader.open = Mock()
        message = reader.get(10)

        # validation
        reader.open.assert_called_once_with()
        receiver.fetch.assert_called_once_with(timeout=10)
        self.assertEqual(msg, message)
        self.assertFalse(sleep.called)

    @patch('gofer.messaging.adapter.qpid.consumer.sleep')
    @patch('gofer.messaging.adapter.qpid.consumer.Empty', Empty)
    @patch('gofer.messaging.adapter.qpid.consumer.Endpoint', Mock())
    @patch('gofer.messaging.adapter.qpid.consumer.RLock', Mock())
    def test_get_empty_raised(self, sleep):
        receiver = Mock()
        receiver.fetch.side_effect = Empty

        # test
        reader = Reader(None)
        reader.open = Mock()
        reader._Reader__receiver = receiver
        message = reader.get()

        # validation
        self.assertEqual(message, None)
        self.assertFalse(sleep.called)

    @patch('gofer.messaging.adapter.qpid.consumer.sleep')
    @patch('gofer.messaging.adapter.qpid.consumer.Endpoint', Mock())
    @patch('gofer.messaging.adapter.qpid.consumer.RLock', Mock())
    def test_get_exception_raised(self, sleep):
        receiver = Mock()
        receiver.fetch.side_effect = Exception

        # test
        reader = Reader(None)
        reader.open = Mock()
        reader._Reader__receiver = receiver
        message = reader.get()

        # validation
        sleep.assert_called_with(10)
        self.assertEqual(message, None)

    @patch('gofer.messaging.adapter.qpid.consumer.Ack')
    @patch('gofer.messaging.adapter.qpid.consumer.subject')
    @patch('gofer.messaging.adapter.qpid.consumer.model')
    @patch('gofer.messaging.adapter.qpid.consumer.auth')
    @patch('gofer.messaging.adapter.qpid.consumer.Endpoint', Mock())
    @patch('gofer.messaging.adapter.qpid.consumer.RLock', Mock())
    def test_next(self, auth, model, subject, ack):
        timeout = 10
        ttl = 55
        message = Mock(ttl=ttl, content='test-content')
        subject.return_value = 'test-subject'
        document = Mock()
        auth.validate.return_value = document

        # test
        reader = Reader(None)
        reader.get = Mock(return_value=message)
        reader.authenticator = Mock()
        _next, _ack = reader.next(timeout)

        # validation
        reader.get.assert_called_once_with(timeout)
        auth.validate.assert_called_once_with(reader.authenticator, message.content)
        subject.assert_called_once_with(message)
        model.validate.assert_called_once_with(document)
        ack.assert_called_once_with(reader, message)
        self.assertEqual(_next, document)
        self.assertEqual(_ack, ack.return_value)
        self.assertEqual(_next.ttl, ttl)
        self.assertEqual(_next.subject, subject.return_value)

    @patch('gofer.messaging.adapter.qpid.consumer.subject')
    @patch('gofer.messaging.adapter.qpid.consumer.model.validate')
    @patch('gofer.messaging.adapter.qpid.consumer.auth')
    @patch('gofer.messaging.adapter.qpid.consumer.Endpoint', Mock())
    @patch('gofer.messaging.adapter.qpid.consumer.RLock', Mock())
    def test_next_invalid_document(self, auth, validate, subject):
        message = Mock(ttl=0, content='test-content')
        subject.return_value = 'test-subject'
        document = Mock()
        auth.validate.return_value = document
        validate.side_effect = InvalidDocument('', '', '')

        # test
        reader = Reader(None)
        reader.get = Mock(return_value=message)
        reader.ack = Mock()
        self.assertRaises(InvalidDocument, reader.next)
        reader.ack.assert_called_once_with(message)

    @patch('gofer.messaging.adapter.qpid.consumer.Endpoint', Mock())
    @patch('gofer.messaging.adapter.qpid.consumer.RLock', Mock())
    def test_next_nothing(self):
        reader = Reader(None)
        reader.get = Mock(return_value=None)
        document, ack = reader.next()
        self.assertEqual(document, None)
        self.assertEqual(ack, None)

    @patch('gofer.messaging.adapter.qpid.consumer.Endpoint', Mock())
    @patch('gofer.messaging.adapter.qpid.consumer.RLock')
    def test_lock(self, lock):
        reader = Reader(None)
        reader._Reader__lock()
        lock.return_value.acquire.assert_called_once_with()

    @patch('gofer.messaging.adapter.qpid.consumer.Endpoint', Mock())
    @patch('gofer.messaging.adapter.qpid.consumer.RLock')
    def test_unlock(self, lock):
        reader = Reader(None)
        reader._Reader__unlock()
        lock.return_value.release.assert_called_once_with()
