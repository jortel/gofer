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

from gofer.messaging import Node
from gofer.messaging.consumer import ConsumerThread, Consumer
from gofer.messaging import InvalidDocument, ValidationFailed


class TestConsumerThread(TestCase):

    def test_init(self):
        url = 'test-url'
        node = Node('test-queue')
        consumer = ConsumerThread(node, url)
        self.assertEqual(consumer.node, node)
        self.assertEqual(consumer.url, url)
        self.assertEqual(consumer.wait, 3)
        self.assertTrue(isinstance(consumer, Thread))
        self.assertTrue(consumer.daemon)
        self.assertEqual(consumer.reader,  None)

    @patch('gofer.common.Thread.abort')
    def test_shutdown(self, abort):
        url = 'test-url'
        node = Node('test-queue')
        consumer = ConsumerThread(node, url)
        consumer.shutdown()
        abort.assert_called_once_with()

    @patch('gofer.messaging.consumer.Reader')
    def test_run(self, reader):
        url = 'test-url'
        node = Node('test-queue')
        consumer = ConsumerThread(node, url)
        consumer.open = Mock()
        consumer.close = Mock()
        consumer.read = Mock(side_effect=StopIteration)

        # test
        try:
            consumer.run()
        except StopIteration:
            pass

        # validation
        reader.assert_called_once_with(node, url)
        consumer.open.assert_called_once_with()
        consumer.read.assert_called_once_with()
        consumer.close.assert_called_once_with()

    def test_open(self):
        url = 'test-url'
        node = Node('test-queue')
        consumer = ConsumerThread(node, url)
        consumer.reader = Mock()

        # test
        consumer.open()

        # validation
        consumer.reader.open.assert_called_once_with()

    def test_close(self):
        url = 'test-url'
        node = Node('test-queue')
        consumer = ConsumerThread(node, url)
        consumer.reader = Mock()

        # test
        consumer.close()

        # validation
        consumer.reader.close.assert_called_once_with()

    def test_close_exception(self):
        url = 'test-url'
        node = Node('test-queue')
        consumer = ConsumerThread(node, url)
        consumer.reader = Mock()
        consumer.reader.close.side_effect = ValueError

        # test
        consumer.close()

        # validation
        consumer.reader.close.assert_called_once_with()

    @patch('gofer.messaging.consumer.sleep')
    def test_open_exception(self, sleep):
        url = 'test-url'
        node = Node('test-queue')
        consumer = ConsumerThread(node, url)
        consumer.reader = Mock()
        consumer.reader.open.side_effect = [ValueError, None]

        # test
        consumer.open()

        # validation
        sleep.assert_called_once_with(30)
        self.assertEqual(consumer.reader.open.call_count, 2)

    def test_read(self):
        url = 'test-url'
        node = Node('test-queue')
        message = Mock()
        document = Mock()
        consumer = ConsumerThread(node, url)
        consumer.reader = Mock()
        consumer.reader.next.return_value = (message, document)
        consumer.dispatch = Mock()

        # test
        consumer.read()

        # validate
        consumer.reader.next.assert_called_once_with(consumer.wait)
        consumer.dispatch.assert_called_once_with(document)
        message.ack.assert_called_once_with()

    def test_read_nothing(self):
        url = 'test-url'
        node = Node('test-queue')
        consumer = ConsumerThread(node, url)
        consumer.reader = Mock()
        consumer.reader.next.return_value = (None, None)
        consumer.dispatch = Mock()

        # test
        consumer.read()

        # validate
        self.assertFalse(consumer.dispatch.called)

    def test_read_validation_failed(self):
        url = 'test-url'
        node = Node('test-queue')
        failed = ValidationFailed(details='test')
        consumer = ConsumerThread(node, url)
        consumer.reader = Mock()
        consumer.reader.next.side_effect = failed
        consumer.rejected = Mock()

        # test
        consumer.read()

        # validate
        consumer.rejected.assert_called_once_with(
            failed.code, failed.description, failed.document, failed.details)

    def test_read_invalid_document(self):
        url = 'test-url'
        node = Node('test-queue')
        code = 12
        description = 'just up and failed'
        document = Mock()
        details = 'crashed'
        ir = InvalidDocument(code, description, document, details)
        consumer = ConsumerThread(node, url)
        consumer.reader = Mock()
        consumer.reader.next.side_effect = ir
        consumer.rejected = Mock()

        # test
        consumer.read()

        # validate
        consumer.rejected.assert_called_once_with(
            ir.code, ir.description, ir.document, ir.details)

    @patch('gofer.messaging.consumer.sleep')
    def test_read_exception(self, sleep):
        url = 'test-url'
        node = Node('test-queue')
        consumer = ConsumerThread(node, url)
        consumer.reader = Mock()
        consumer.reader.next.side_effect = IndexError
        consumer.open = Mock()
        consumer.close = Mock()

        # test
        consumer.read()

        # validation
        consumer.close.assert_called_once_with()
        consumer.open.assert_called_once_with()
        sleep.assert_called_once_with(60)

    def test_rejected(self):
        url = 'test-url'
        node = Node('test-queue')
        consumer = ConsumerThread(node, url)
        consumer.rejected('1', '2', '3', '4')

    def test_dispatch(self):
        url = 'test-url'
        node = Node('test-queue')
        consumer = ConsumerThread(node, url)
        consumer.dispatch(Mock())


class TestConsumer(TestCase):

    @patch('gofer.messaging.consumer.Reader', Mock())
    def test_init(self):
        url = 'test-url'
        node = Node('test-queue')

        # test
        consumer = Consumer(node, url)

        # validation
        self.assertEqual(consumer.node, node)
        self.assertEqual(consumer.url, url)
