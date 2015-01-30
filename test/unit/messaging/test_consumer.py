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

from threading import Thread
from unittest import TestCase

from mock import Mock, patch


from gofer.messaging.consumer import ConsumerThread, Consumer
from gofer.messaging import InvalidDocument, ValidationFailed


class Queue(object):

    def __init__(self, name):
        self.name = name


class TestConsumerThread(TestCase):

    def test_init(self):
        url = 'test-url'
        queue = Queue('test-queue')
        consumer = ConsumerThread(queue, url)
        self.assertEqual(consumer.queue, queue)
        self.assertEqual(consumer.url, url)
        self.assertTrue(isinstance(consumer, Thread))
        self.assertTrue(consumer.daemon)
        self.assertEqual(consumer._reader,  None)
        self.assertTrue(consumer._run)

    def test_stop(self):
        url = 'test-url'
        queue = Queue('test-queue')
        consumer = ConsumerThread(queue, url)
        consumer.stop()
        self.assertFalse(consumer._run)

    @patch('gofer.messaging.consumer.Reader')
    def test_run(self, reader):
        url = 'test-url'
        queue = Queue('test-queue')
        consumer = ConsumerThread(queue, url)
        consumer._open = Mock()
        consumer._close = Mock()
        consumer._read = Mock(side_effect=StopIteration)

        # test
        try:
            consumer.run()
        except StopIteration:
            pass

        # validation
        reader.assert_called_once_with(queue, url)
        consumer._open.assert_called_once_with()
        consumer._read.assert_called_once_with()
        consumer._close.assert_called_once_with()

    def test_open(self):
        url = 'test-url'
        queue = Queue('test-queue')
        consumer = ConsumerThread(queue, url)
        consumer._reader = Mock()

        # test
        consumer._open()

        # validation
        consumer._reader.open.assert_called_once_with()

    def test_close(self):
        url = 'test-url'
        queue = Queue('test-queue')
        consumer = ConsumerThread(queue, url)
        consumer._reader = Mock()

        # test
        consumer._close()

        # validation
        consumer._reader.close.assert_called_once_with()

    def test_close_exception(self):
        url = 'test-url'
        queue = Queue('test-queue')
        consumer = ConsumerThread(queue, url)
        consumer._reader = Mock()
        consumer._reader.close.side_effect = ValueError

        # test
        consumer._close()

        # validation
        consumer._reader.close.assert_called_once_with()

    @patch('gofer.messaging.consumer.sleep')
    def test_open_exception(self, sleep):
        url = 'test-url'
        queue = Queue('test-queue')
        consumer = ConsumerThread(queue, url)
        consumer._reader = Mock()
        consumer._reader.open.side_effect = [ValueError, None]

        # test
        consumer._open()

        # validation
        sleep.assert_called_once_with(60)
        self.assertEqual(consumer._reader.open.call_count, 2)

    def test_read(self):
        url = 'test-url'
        queue = Queue('test-queue')
        message = Mock()
        document = Mock()
        consumer = ConsumerThread(queue, url)
        consumer._reader = Mock()
        consumer._reader.next.return_value = (message, document)
        consumer.dispatch = Mock()

        # test
        consumer._read()

        # validate
        consumer.dispatch.assert_called_once_with(document)
        message.ack.assert_called_once_with()

    def test_read_nothing(self):
        url = 'test-url'
        queue = Queue('test-queue')
        consumer = ConsumerThread(queue, url)
        consumer._reader = Mock()
        consumer._reader.next.return_value = (None, None)
        consumer.dispatch = Mock()

        # test
        consumer._read()

        # validate
        self.assertFalse(consumer.dispatch.called)

    def test_read_validation_failed(self):
        url = 'test-url'
        queue = Queue('test-queue')
        failed = ValidationFailed(details='test')
        consumer = ConsumerThread(queue, url)
        consumer._reader = Mock()
        consumer._reader.next.side_effect = failed
        consumer._rejected = Mock()

        # test
        consumer._read()

        # validate
        consumer._rejected.assert_called_once_with(
            failed.code, failed.description, failed.document, failed.details)

    def test_read_invalid_document(self):
        url = 'test-url'
        queue = Queue('test-queue')
        code = 12
        description = 'just up and failed'
        document = Mock()
        details = 'crashed'
        ir = InvalidDocument(code, description, document, details)
        consumer = ConsumerThread(queue, url)
        consumer._reader = Mock()
        consumer._reader.next.side_effect = ir
        consumer._rejected = Mock()

        # test
        consumer._read()

        # validate
        consumer._rejected.assert_called_once_with(
            ir.code, ir.description, ir.document, ir.details)

    @patch('gofer.messaging.consumer.sleep')
    def test_read_exception(self, sleep):
        url = 'test-url'
        queue = Queue('test-queue')
        consumer = ConsumerThread(queue, url)
        consumer._reader = Mock()
        consumer._reader.next.side_effect = IndexError
        consumer._open = Mock()
        consumer._close = Mock()

        # test
        consumer._read()

        # validation
        consumer._close.assert_called_once_with()
        consumer._open.assert_called_once_with()
        sleep.assert_called_once_with(60)

    def test_rejected(self):
        url = 'test-url'
        queue = Queue('test-queue')
        consumer = ConsumerThread(queue, url)
        consumer._rejected('1', '2', '3', '4')

    def test_dispatch(self):
        url = 'test-url'
        queue = Queue('test-queue')
        consumer = ConsumerThread(queue, url)
        consumer.dispatch(Mock())


class TestConsumer(TestCase):

    @patch('gofer.messaging.consumer.Reader')
    def test_init(self, reader):
        queue = Mock()
        url = 'test-url'

        # test
        consumer = Consumer(queue, url)

        # validation
        self.assertEqual(consumer.queue, queue)
        self.assertEqual(consumer.url, url)
