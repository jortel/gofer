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

from gofer.messaging.model import VERSION, Document
from gofer.messaging.adapter.model import Destination
from gofer.devel import ipatch

with ipatch('qpid.messaging'):
    from gofer.messaging.adapter.qpid.producer import send, plain_send
    from gofer.messaging.adapter.qpid.producer import Producer, BaseProducer
    from gofer.messaging.adapter.qpid.producer import PlainProducer, BasePlainProducer


class TestSend(TestCase):

    @patch('gofer.messaging.adapter.qpid.producer.uuid4')
    @patch('gofer.messaging.adapter.qpid.producer.Message')
    @patch('gofer.messaging.adapter.qpid.producer.auth')
    def test_send(self, auth, message, uuid4):
        ttl = 10
        _id = 'test-id'
        signed = 'signed-document'
        authenticator = Mock()
        sender = Mock()
        channel = Mock()
        channel.sender.return_value = sender
        endpoint = Mock(authenticator=authenticator)
        endpoint.id.return_value = _id
        endpoint.channel.return_value = channel
        auth.sign.return_value = signed
        uuid4.return_value = '12345'
        destination = Destination('elmer')
        body = {
            'A': 1,
            'B': 2
        }
        unsigned = Document(
            sn=uuid4.return_value,
            version=VERSION,
            routing=[_id, destination.routing_key],
            **body)

        # test
        sn = send(endpoint, destination, ttl=ttl, **body)

        # validation
        auth.sign.assert_called_once_with(authenticator, unsigned.dump())
        message.assert_called_once_with(content=signed, durable=True, ttl=ttl)
        endpoint.channel.assert_called_once_with()
        channel.sender.assert_called_once_with('elmer')
        sender.send.assert_called_once_with(message.return_value)
        sender.close.assert_called_once_with()
        self.assertEqual(sn, uuid4.return_value)

    @patch('gofer.messaging.adapter.qpid.producer.uuid4')
    @patch('gofer.messaging.adapter.qpid.producer.Message')
    @patch('gofer.messaging.adapter.qpid.producer.auth')
    def test_send_explicit_exchange(self, auth, message, uuid4):
        ttl = 10
        _id = 'test-id'
        signed = 'signed-document'
        authenticator = Mock()
        sender = Mock()
        channel = Mock()
        channel.sender.return_value = sender
        endpoint = Mock(authenticator=authenticator)
        endpoint.id.return_value = _id
        endpoint.channel.return_value = channel
        auth.sign.return_value = signed
        uuid4.return_value = '12345'
        destination = Destination('elmer', exchange='direct')
        body = {
            'A': 1,
            'B': 2
        }
        unsigned = Document(
            sn=uuid4.return_value,
            version=VERSION,
            routing=[_id, destination.routing_key],
            **body)

        # test
        sn = send(endpoint, destination, ttl=ttl, **body)

        # validation
        auth.sign.assert_called_once_with(authenticator, unsigned.dump())
        message.assert_called_once_with(content=signed, durable=True, ttl=ttl)
        endpoint.channel.assert_called_once_with()
        channel.sender.assert_called_once_with('direct/elmer')
        sender.send.assert_called_once_with(message.return_value)
        sender.close.assert_called_once_with()
        self.assertEqual(sn, uuid4.return_value)


class TestPlainSend(TestCase):

    @patch('gofer.messaging.adapter.qpid.producer.Message')
    def test_send(self, message):
        ttl = 10
        _id = 'msg-id'
        message.return_value.id = _id
        sender = Mock()
        channel = Mock()
        channel.sender.return_value = sender
        endpoint = Mock()
        endpoint.channel.return_value = channel
        destination = Destination('elmer')
        content = 'hello'

        # test
        msg_id = plain_send(endpoint, destination, content, ttl=ttl)

        # validation
        message.assert_called_once_with(content=content, durable=True, ttl=ttl)
        endpoint.channel.assert_called_once_with()
        channel.sender.assert_called_once_with('elmer')
        sender.send.assert_called_once_with(message.return_value)
        sender.close.assert_called_once_with()
        self.assertEqual(msg_id, _id)

    @patch('gofer.messaging.adapter.qpid.producer.Message')
    def test_send_explicit_exchange(self, message):
        ttl = 10
        _id = 'msg-id'
        message.return_value.id = _id
        sender = Mock()
        channel = Mock()
        channel.sender.return_value = sender
        endpoint = Mock()
        endpoint.channel.return_value = channel
        destination = Destination('elmer', exchange='direct')
        content = 'hello'

        # test
        msg_id = plain_send(endpoint, destination, content, ttl=ttl)

        # validation
        message.assert_called_once_with(content=content, durable=True, ttl=ttl)
        endpoint.channel.assert_called_once_with()
        channel.sender.assert_called_once_with('direct/elmer')
        sender.send.assert_called_once_with(message.return_value)
        sender.close.assert_called_once_with()
        self.assertEqual(msg_id, _id)


class TestProducer(TestCase):

    @patch('gofer.messaging.adapter.qpid.producer.Endpoint')
    def test_init(self, endpoint):
        url = 'test-url'

        # test
        producer = Producer(url)

        # validation
        endpoint.assert_called_once_with(url)
        self.assertEqual(producer._endpoint, endpoint.return_value)
        self.assertTrue(isinstance(producer, BaseProducer))

    @patch('gofer.messaging.adapter.qpid.producer.Endpoint', Mock())
    def test_endpoint_property(self):
        producer = Producer('')
        self.assertEqual(producer.endpoint(), producer._endpoint)

    @patch('gofer.messaging.adapter.qpid.producer.send')
    def test_send(self, send):
        ttl = 10
        sn = 1234
        send.return_value = sn
        destination = Mock()
        body = {
            'A': 1,
            'B': 2
        }

        # test
        producer = Producer('')
        _sn = producer.send(destination, ttl=ttl, **body)

        # validation
        send.assert_called_once_with(producer, destination, ttl, **body)
        self.assertEqual(_sn, sn)

    @patch('gofer.messaging.adapter.qpid.producer.send')
    def test_broadcast(self, send):
        ttl = 10
        sn_list = [1234, 5678]
        send.side_effect = sn_list
        destinations = [
            Destination('q1'),
            Destination('q2')
        ]
        body = {
            'A': 1,
            'B': 2
        }

        # test
        producer = Producer('')
        _sn_list = producer.broadcast(destinations, ttl=ttl, **body)

        # validation
        self.assertEqual(
            send.call_args_list,
            [
                ((producer, destinations[0], ttl), body),
                ((producer, destinations[1], ttl), body),
            ])
        self.assertEqual(
            _sn_list,
            [
                (repr(destinations[0]), sn_list[0]),
                (repr(destinations[1]), sn_list[1]),
            ])


class TestPlainProducer(TestCase):

    @patch('gofer.messaging.adapter.qpid.producer.Endpoint')
    def test_init(self, endpoint):
        url = 'test-url'

        # test
        producer = PlainProducer(url)

        # validation
        endpoint.assert_called_once_with(url)
        self.assertEqual(producer._endpoint, endpoint.return_value)
        self.assertTrue(isinstance(producer, BasePlainProducer))

    @patch('gofer.messaging.adapter.qpid.producer.Endpoint', Mock())
    def test_endpoint_property(self):
        producer = PlainProducer('')
        self.assertEqual(producer.endpoint(), producer._endpoint)

    @patch('gofer.messaging.adapter.qpid.producer.plain_send')
    def test_send(self, send):
        ttl = 10
        sn = 1234
        send.return_value = sn
        destination = Mock()
        content = 'test-content'

        # test
        producer = PlainProducer('')
        _sn = producer.send(destination, content, ttl=ttl)

        # validation
        send.assert_called_once_with(producer, destination, content, ttl=ttl)
        self.assertEqual(_sn, sn)

    @patch('gofer.messaging.adapter.qpid.producer.plain_send')
    def test_broadcast(self, send):
        ttl = 10
        sn_list = [1234, 5678]
        send.side_effect = sn_list
        destinations = [
            Destination('q1'),
            Destination('q2')
        ]
        content = 'test-content'

        # test
        producer = PlainProducer('')
        _sn_list = producer.broadcast(destinations, content, ttl=ttl)

        # validation
        self.assertEqual(
            send.call_args_list,
            [
                ((producer, destinations[0], content), dict(ttl=ttl)),
                ((producer, destinations[1], content), dict(ttl=ttl)),
            ])
        self.assertEqual(
            _sn_list,
            [
                (repr(destinations[0]), sn_list[0]),
                (repr(destinations[1]), sn_list[1]),
            ])