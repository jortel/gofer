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

with ipatch('qpid'):
    from gofer.messaging.adapter.qpid.producer import BaseSender, Sender


class TestPlainSend(TestCase):

    @patch('gofer.messaging.adapter.qpid.producer.Endpoint')
    def test_init(self, endpoint):
        url = 'http://host'

        # test
        sender = Sender(url)

        # validation
        endpoint.assert_called_once_with(url)
        self.assertEqual(sender.url, url)
        self.assertEqual(sender._endpoint, endpoint.return_value)
        self.assertEqual(sender._link, None)
        self.assertTrue(isinstance(sender, BaseSender))

    @patch('gofer.messaging.adapter.qpid.producer.Endpoint', Mock())
    def test_endpoint(self):
        sender = Sender('')
        # unlinked
        self.assertEqual(sender.endpoint(), sender._endpoint)
        # linked
        sender._link = Mock()
        self.assertEqual(sender.endpoint(), sender._link)

    @patch('gofer.messaging.adapter.qpid.producer.Endpoint', Mock())
    def test_link(self):
        other = Mock()
        sender = Sender('')
        self.assertEqual(sender._link, None)
        sender.link(other)
        self.assertEqual(sender._link, other.endpoint.return_value)

    @patch('gofer.messaging.adapter.qpid.producer.Endpoint', Mock())
    def test_unlink(self):
        sender = Sender('')
        sender._link = Mock()
        sender.unlink()
        self.assertEqual(sender._link, None)

    @patch('gofer.messaging.adapter.qpid.producer.Message')
    @patch('gofer.messaging.adapter.qpid.producer.Endpoint')
    def test_send(self, endpoint, message):
        ttl = 10
        _sender = Mock()
        channel = Mock()
        channel.sender.return_value = _sender
        endpoint.return_value.channel.return_value = channel
        route = 'q1'
        content = 'hello'

        # test
        sender = Sender('')
        sender.send(route, content, ttl=ttl)

        # validation
        message.assert_called_once_with(content=content, durable=True, ttl=ttl)
        endpoint.return_value.channel.assert_called_once_with()
        channel.sender.assert_called_once_with(route)
        _sender.send.assert_called_once_with(message.return_value)
        _sender.close.assert_called_once_with()
