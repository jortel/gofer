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
#
# Jeff Ortel <jortel@redhat.com>
#

from unittest import TestCase

from mock import patch, Mock

from gofer.devel import ipatch
from gofer.common import ThreadSingleton

with ipatch('amqp'):
    from gofer.messaging.adapter.model import Broker
    from gofer.messaging.adapter.amqp.connection import Connection, BaseConnection
    from gofer.messaging.adapter.amqp.connection import CONNECTION_EXCEPTIONS

TEST_URL = 'amqp+amqps://elmer:fudd@redhat.com:1234/test-virtual-host'


class TestConnection(TestCase):

    def setUp(self):
        ThreadSingleton.all().clear()

    def tearDown(self):
        ThreadSingleton.all().clear()

    def test_init(self):
        url = TEST_URL
        c = Connection(url)
        self.assertTrue(isinstance(c, BaseConnection))
        self.assertEqual(c.url, url)

    @patch('gofer.messaging.adapter.amqp.connection.Domain.broker.find')
    @patch('gofer.messaging.adapter.amqp.connection.Connection._ssl')
    @patch('gofer.messaging.adapter.amqp.connection.RealConnection')
    def test_open(self, connection, _ssl, find):
        url = TEST_URL
        broker = Broker(url)
        broker.ssl.ca_certificate = 'test-ca'
        broker.ssl.client_key = 'test-key'
        broker.ssl.client_certificate = 'test-crt'
        find.return_value = broker

        # test
        c = Connection(url)
        c._ssh = Mock()
        c.open()

        # validation
        _ssl.assert_called_once_with(broker)
        connection.assert_called_once_with(
            host=':'.join((broker.host, str(broker.port))),
            virtual_host=broker.virtual_host,
            userid=broker.userid,
            password=broker.password,
            ssl=_ssl.return_value,
            confirm_publish=True)

        self.assertEqual(c._impl, connection.return_value)

    def test_open_already(self):
        url = TEST_URL
        c = Connection(url)
        c._impl = Mock()
        c.open()
        self.assertFalse(c._impl.open.called)

    @patch('gofer.messaging.adapter.amqp.connection.sleep')
    @patch('gofer.messaging.adapter.amqp.connection.RealConnection')
    def test_open_with_retry(self, connection, sleep):
        url = TEST_URL
        side_effect = [CONNECTION_EXCEPTIONS[0], Mock()]
        connection.side_effect = side_effect

        # test
        c = Connection(url)
        c._ssh = Mock()
        c.open(delay=10)

        # validation
        sleep.assert_called_once_with(10)
        self.assertEqual(connection.call_count, 2)
        self.assertEqual(c._impl, side_effect[1])

    @patch('gofer.messaging.adapter.amqp.connection.sleep')
    @patch('gofer.messaging.adapter.amqp.connection.RealConnection')
    def test_open_with_no_retry(self, connection, sleep):
        url = TEST_URL
        side_effect = [CONNECTION_EXCEPTIONS[0], Mock()]
        connection.side_effect = side_effect

        # test
        c = Connection(url)
        c._ssh = Mock()
        self.assertRaises(CONNECTION_EXCEPTIONS[0], c.open, retries=0)

        # validation
        self.assertFalse(sleep.called)
        self.assertEqual(connection.call_count, 1)

    def test_channel(self):
        url = TEST_URL
        c = Connection(url)
        c._impl = Mock()
        ch = c.channel()
        self.assertEqual(ch, c._impl.channel.return_value)

    def test_close(self):
        url = 'test-url'
        c = Connection(url)
        impl = Mock()
        impl.close.side_effect = ValueError
        c._impl = impl
        c.close()
        impl.close.assert_called_once_with()
        self.assertEqual(c._impl, None)

    def test_ssl(self):
        url = TEST_URL

        # test
        b = Broker(url)
        b.ssl.ca_certificate = 'test-ca'
        b.ssl.client_key = 'test-key'
        b.ssl.client_certificate = 'test-crt'
        ssl = Connection._ssl(b)

        # validation
        self.assertEqual(
            ssl,
            {
                'ca_certs': b.ssl.ca_certificate,
                'cert_reqs': 2,
                'certfile': b.ssl.client_certificate,
                'keyfile': b.ssl.client_key
            })

    def test_ssl_no_certs(self):
        url = TEST_URL

        # test
        b = Broker(url)
        ssl = Connection._ssl(b)

        # validation
        self.assertEqual(ssl, None)

    def test_ssl_not_ssl(self):
        url = 'amqp://elmer:fudd@redhat.com:1234'

        # test
        b = Broker(url)
        ssl = Connection._ssl(b)

        self.assertEqual(str(b.url), url)

        # validation
        self.assertEqual(ssl, None)