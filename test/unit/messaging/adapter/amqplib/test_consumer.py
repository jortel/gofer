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

    @patch('gofer.messaging.adapter.amqplib.consumer.Reader.channel')
    def test_get(self, channel):
        queue = Mock(name='test-queue')
        received = Mock(body='<body/>')
        channel.return_value.basic_get.return_value = received
        url = 'test-url'

        # test
        reader = Reader(queue, url=url)
        message = reader.get()

        # validation
        channel.return_value.basic_get.assert_called_once_with(queue.name)
        self.assertTrue(isinstance(message, Message))
        self.assertEqual(message._reader, reader)
        self.assertEqual(message._impl, received)
        self.assertEqual(message._body, message.body)

    @patch('gofer.messaging.adapter.amqplib.consumer.Reader.channel')
    def test_get_nothing(self, channel):
        queue = Mock(name='test-queue')
        channel.return_value.basic_get.return_value = None
        url = 'test-url'

        # test
        reader = Reader(queue, url=url)
        message = reader.get()

        # validation
        channel.return_value.basic_get.assert_called_once_with(queue.name)
        self.assertEqual(message, None)
