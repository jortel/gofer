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

from mock import patch, Mock

from gofer.devel import ipatch
from gofer import ThreadSingleton
from gofer.messaging.adapter.model import Broker, NotFound

with ipatch('proton'):
    from gofer.messaging.adapter.proton.connection import Connection


class ConnectionException(Exception):
    pass


class LinkException(Exception):
    pass


class TestConnection(TestCase):

    def setUp(self):
        ThreadSingleton.all().clear()

    def tearDown(self):
        ThreadSingleton.all().clear()

    @patch('gofer.messaging.adapter.proton.connection.SSLDomain')
    def test_ssl_domain(self, ssl_domain):
        ssl_domain.MODE_CLIENT = 0x01
        ssl_domain.VERIFY_PEER = 0x02
        ssl_domain.VERIFY_PEER_NAME = 0x03
        broker = Broker()
        broker.ssl.ca_certificate = 'ca'
        broker.ssl.client_certificate = 'client'
        broker.ssl.client_key = 'key'

        # test
        domain = Connection.ssl_domain(broker)

        # validation
        ssl_domain.assert_called_once_with(ssl_domain.MODE_CLIENT)
        domain.set_trusted_ca_db.assert_called_once_with(broker.ssl.ca_certificate)
        domain.set_credentials.assert_called_once_with(
            broker.ssl.client_certificate,
            broker.ssl.client_key, None)
        domain.set_peer_authentication.assert_called_once_with(ssl_domain.VERIFY_PEER)

    @patch('gofer.messaging.adapter.proton.connection.SSLDomain')
    def test_ssl_domain_host_validation(self, ssl_domain):
        ssl_domain.MODE_CLIENT = 0x01
        ssl_domain.VERIFY_PEER = 0x02
        ssl_domain.VERIFY_PEER_NAME = 0x03
        broker = Broker()
        broker.ssl.ca_certificate = 'ca'
        broker.ssl.client_certificate = 'client'
        broker.ssl.client_key = 'key'
        broker.ssl.host_validation = True

        # test
        domain = Connection.ssl_domain(broker)

        # validation
        ssl_domain.assert_called_once_with(ssl_domain.MODE_CLIENT)
        domain.set_trusted_ca_db.assert_called_once_with(broker.ssl.ca_certificate)
        domain.set_credentials.assert_called_once_with(
            broker.ssl.client_certificate,
            broker.ssl.client_key, None)
        domain.set_peer_authentication.assert_called_once_with(ssl_domain.VERIFY_PEER_NAME)

    def test_init(self):
        url = 'test-url'
        connection = Connection(url)
        self.assertEqual(connection.url, url)
        self.assertEqual(connection._impl, None)

    def test_is_open(self):
        connection = Connection('')
        self.assertFalse(connection.is_open())
        connection._impl = Mock()
        self.assertTrue(connection.is_open())

    @patch('gofer.messaging.adapter.proton.connection.BlockingConnection')
    @patch('gofer.messaging.adapter.proton.connection.Connection.ssl_domain')
    def test_open(self, ssl_domain, blocking):
        url = 'test-url'
        connection = Connection(url)

        # test
        connection.open()

        # validation
        url = 'amqp://%s' % url
        blocking.assert_called_once_with(url, ssl_domain=ssl_domain.return_value)

    @patch('gofer.messaging.adapter.proton.connection.sleep')
    @patch('gofer.messaging.adapter.proton.connection.BlockingConnection')
    @patch('gofer.messaging.adapter.proton.connection.ConnectionException', ConnectionException)
    def test_open_with_retry(self, blocking, sleep):
        url = 'test-url'
        blocking.side_effect = [ConnectionException, None]

        # test
        connection = Connection(url)
        connection.open(delay=10)

        # validation
        sleep.assert_called_once_with(10)
        self.assertEqual(blocking.call_count, 2)

    @patch('gofer.messaging.adapter.proton.connection.sleep')
    @patch('gofer.messaging.adapter.proton.connection.BlockingConnection')
    @patch('gofer.messaging.adapter.proton.connection.ConnectionException', ConnectionException)
    def test_open_with_retry_exceeded(self, blocking, sleep):
        url = 'test-url'
        connection = Connection(url)
        blocking.side_effect = ConnectionException

        # test
        self.assertRaises(ConnectionException, connection.open, retries=1, delay=10)

        # validation
        sleep.assert_called_once_with(10)
        self.assertEqual(blocking.call_count, 2)

    @patch('gofer.messaging.adapter.proton.connection.BlockingConnection')
    def test_open_already(self, blocking):
        url = 'test-url'
        connection = Connection(url)
        connection.is_open = Mock(return_value=True)

        # test
        connection.open()

        # validation
        self.assertFalse(blocking.called)

    @patch('gofer.messaging.adapter.proton.connection.uuid4')
    def test_sender(self, uuid):
        url = 'test-url'
        address = 'test'
        uuid.return_value = '1234'
        connection = Connection(url)
        connection._impl = Mock()

        # test
        sender = connection.sender(address)

        # validation
        connection._impl.create_sender.assert_called_once_with(address, name=uuid.return_value)
        self.assertEqual(sender, connection._impl.create_sender.return_value)

    @patch('gofer.messaging.adapter.proton.connection.uuid4')
    @patch('gofer.messaging.adapter.proton.connection.LinkException', LinkException)
    def test_sender_not_found(self, uuid):
        url = 'test-url'
        address = 'test'
        uuid.return_value = '1234'
        connection = Connection(url)
        connection._impl = Mock()
        connection._impl.create_sender.side_effect = LinkException

        # test
        self.assertRaises(NotFound, connection.sender, address)

    @patch('gofer.messaging.adapter.proton.connection.DynamicNodeProperties')
    @patch('gofer.messaging.adapter.proton.connection.uuid4')
    def test_receiver(self, uuid, properties):
        url = 'test-url'
        address = 'test'
        uuid.return_value = '1234'
        connection = Connection(url)
        connection._impl = Mock()

        # test
        receiver = connection.receiver(address)

        # validation
        connection._impl.create_receiver.assert_called_once_with(
            address, dynamic=False, name=uuid.return_value, options=None)
        self.assertEqual(receiver, connection._impl.create_receiver.return_value)
        self.assertFalse(properties.called)

    @patch('gofer.messaging.adapter.proton.connection.DynamicNodeProperties')
    @patch('gofer.messaging.adapter.proton.connection.uuid4')
    def test_dynamic_receiver(self, uuid, properties):
        url = 'test-url'
        address = 'test'
        uuid.return_value = '1234'
        connection = Connection(url)
        connection._impl = Mock()

        # test
        receiver = connection.receiver(address, dynamic=True)

        # validation
        properties.assert_called_once_with({'x-opt-qd.address': address})
        connection._impl.create_receiver.assert_called_once_with(
            None, dynamic=True, name=uuid.return_value, options=properties.return_value)
        self.assertEqual(receiver, connection._impl.create_receiver.return_value)

    @patch('gofer.messaging.adapter.proton.connection.uuid4')
    @patch('gofer.messaging.adapter.proton.connection.LinkException', LinkException)
    def test_receiver_not_found(self, uuid):
        url = 'test-url'
        address = 'test'
        uuid.return_value = '1234'
        connection = Connection(url)
        connection._impl = Mock()
        connection._impl.create_receiver.side_effect = LinkException

        # test
        self.assertRaises(NotFound, connection.receiver, address)

    def test_close(self):
        url = 'test-url'
        c = Connection(url)
        impl = Mock()
        impl.close.side_effect = ValueError
        c._impl = impl
        c.close()
        impl.close.assert_called_once_with()
        self.assertEqual(c._impl, None)
