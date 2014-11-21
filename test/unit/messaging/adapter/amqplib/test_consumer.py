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

with ipatch('amqplib'):
    from gofer.messaging.adapter.amqplib.consumer import Reader, BaseReader


class TestReader(TestCase):

    @patch('gofer.messaging.adapter.amqplib.consumer.Endpoint')
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
        self.assertEqual(reader._endpoint, endpoint.return_value)

    @patch('gofer.messaging.adapter.amqplib.consumer.Endpoint', Mock())
    def test_endpoint(self):
        reader = Reader(None)
        returned = reader.endpoint()
        self.assertEqual(returned, reader._endpoint)

    @patch('gofer.messaging.adapter.amqplib.consumer.Endpoint', Mock())
    def test_get(self):
        queue = Mock(name='test-queue')
        url = 'test-url'

        # test
        reader = Reader(queue, url=url)
        reader.channel = Mock()
        message = reader.get()

        # validation
        reader.channel.assert_called()
        reader.channel.return_value.basic_get.assert_called_once_with(queue.name)
        self.assertEqual(message, reader.channel.return_value.basic_get.return_value)

    @patch('gofer.messaging.adapter.amqplib.consumer.Ack')
    @patch('gofer.messaging.adapter.amqplib.consumer.model')
    @patch('gofer.messaging.adapter.amqplib.consumer.auth')
    @patch('gofer.messaging.adapter.amqplib.consumer.Endpoint', Mock())
    def test_next(self, auth, model, ack):
        message = Mock(body='test-content')
        document = Mock()
        auth.validate.return_value = document

        # test
        reader = Reader(None)
        reader.get = Mock(return_value=message)
        reader.authenticator = Mock()
        _next, _ack = reader.next()

        # validation
        reader.get.assert_called_once_with()
        auth.validate.assert_called_once_with(reader.authenticator, message.body)
        model.validate.assert_called_once_with(document)
        ack.assert_called_once_with(reader, message)
        self.assertEqual(_next, document)
        self.assertEqual(_ack, ack.return_value)

    @patch('gofer.messaging.adapter.amqplib.consumer.model.validate')
    @patch('gofer.messaging.adapter.amqplib.consumer.auth')
    @patch('gofer.messaging.adapter.amqplib.consumer.Endpoint', Mock())
    def test_next_invalid_document(self, auth, validate):
        message = Mock(body='test-content')
        document = Mock()
        auth.validate.return_value = document
        validate.side_effect = InvalidDocument('', '', '')

        # test
        reader = Reader(None)
        reader.get = Mock(return_value=message)
        reader.ack = Mock()
        self.assertRaises(InvalidDocument, reader.next)
        reader.ack.assert_called_once_with(message)

    @patch('gofer.messaging.adapter.amqplib.consumer.Endpoint', Mock())
    def test_next_nothing(self):
        reader = Reader(None)
        reader.get = Mock(return_value=None)
        document, ack = reader.next(timeout=0)
        self.assertEqual(document, None)
        self.assertEqual(ack, None)

    @patch('gofer.messaging.adapter.amqplib.consumer.sleep')
    @patch('gofer.messaging.adapter.amqplib.consumer.Endpoint', Mock())
    def test_next_nothing_retry(self, sleep):
        reader = Reader(None)
        reader.get = Mock(return_value=None)
        document, ack = reader.next()
        self.assertEqual(document, None)
        self.assertEqual(ack, None)
