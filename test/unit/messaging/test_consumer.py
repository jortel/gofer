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


from gofer.messaging.consumer import BaseConsumer, Consumer
from gofer.messaging import InvalidDocument, ValidationFailed


class TestBaseConsumer(TestCase):

    def test_init(self):
        reader = Mock()
        consumer = BaseConsumer(reader)
        self.assertEqual(consumer.reader, reader)
        self.assertTrue(isinstance(consumer, Thread))
        self.assertTrue(consumer.daemon)
        self.assertTrue(consumer._run)

    def test_stop(self):
        reader = Mock()
        consumer = BaseConsumer(reader)
        consumer.stop()
        self.assertFalse(consumer._run)

    def test_run(self):
        reader = Mock()
        consumer = BaseConsumer(reader)
        consumer._read = Mock(side_effect=StopIteration)

        # test
        try:
            consumer.run()
        except StopIteration:
            pass

        # validation
        reader.open.assert_called_once_with()
        consumer._read.assert_called_once_with()
        reader.close.assert_called_once_with()

    def test_open(self):
        reader = Mock()
        consumer = BaseConsumer(reader)

        # test
        consumer._open()

        # validation
        reader.open.assert_called_once_with()

    def test_close(self):
        reader = Mock()
        consumer = BaseConsumer(reader)

        # test
        consumer._close()

        # validation
        reader.close.assert_called_once_with()

    def test_close_exception(self):
        reader = Mock()
        reader.close.side_effect = ValueError()
        consumer = BaseConsumer(reader)

        # test
        consumer._close()

        # validation
        reader.close.assert_called_once_with()

    @patch('gofer.messaging.consumer.sleep')
    def test_open_exception(self, sleep):
        reader = Mock()
        reader.open.side_effect = [ValueError, None]
        consumer = BaseConsumer(reader)

        # test
        consumer._open()

        # validation
        sleep.assert_called_once_with(60)
        self.assertEqual(reader.open.call_count, 2)

    def test_read(self):
        reader = Mock()
        message = Mock()
        document = Mock()
        reader.next.return_value = (message, document)
        consumer = BaseConsumer(reader)
        consumer.dispatch = Mock()

        # test
        consumer._read()

        # validate
        consumer.dispatch.assert_called_once_with(document)
        message.ack.assert_called_once_with()

    def test_read_nothing(self):
        reader = Mock()
        reader.next.return_value = (None, None)
        consumer = BaseConsumer(reader)
        consumer.dispatch = Mock()

        # test
        consumer._read()

        # validate
        self.assertFalse(consumer.dispatch.called)

    def test_read_validation_failed(self):
        reader = Mock()
        failed = ValidationFailed(details='test')
        reader.next.side_effect = failed
        consumer = BaseConsumer(reader)
        consumer._rejected = Mock()

        # test
        consumer._read()

        # validate
        consumer._rejected.assert_called_once_with(
            failed.code, failed.description, failed.document, failed.details)

    def test_read_invalid_document(self):
        reader = Mock()
        code = 12
        description = 'just up and failed'
        document = Mock()
        details = 'crashed'
        ir = InvalidDocument(code, description, document, details)
        reader.next.side_effect = ir
        consumer = BaseConsumer(reader)
        consumer._rejected = Mock()

        # test
        consumer._read()

        # validate
        consumer._rejected.assert_called_once_with(
            ir.code, ir.description, ir.document, ir.details)

    @patch('gofer.messaging.consumer.sleep')
    def test_read_exception(self, sleep):
        reader = Mock()
        reader.next.side_effect = IndexError
        consumer = BaseConsumer(reader)

        # test
        consumer._read()

        # validation
        reader.close.assert_called_once_with()
        reader.open.assert_called_once_with()
        sleep.assert_called_once_with(60)

    def test_rejected(self):
        reader = Mock()
        consumer = BaseConsumer(reader)
        consumer._rejected('1', '2', '3', '4')

    def test_dispatch(self):
        reader = Mock()
        consumer = BaseConsumer(reader)
        consumer.dispatch(Mock())


class TestConsumer(TestCase):

    @patch('gofer.messaging.consumer.Reader')
    def test_init(self, reader):
        queue = Mock()
        url = 'test-url'

        # test
        consumer = Consumer(queue, url)

        # validation
        self.assertEqual(consumer.reader, reader.return_value)
        self.assertEqual(consumer.queue, queue)
        self.assertEqual(consumer.url, url)
