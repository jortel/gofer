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

from gofer.common import ThreadSingleton
from gofer.devel import ipatch

with ipatch('amqp'):
    from gofer.messaging.adapter.model import Connector
    from gofer.messaging.adapter.amqp.connection import Connection, BaseConnection

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

    @patch('gofer.messaging.adapter.amqp.connection.Connector.find')
    @patch('gofer.messaging.adapter.amqp.connection.Connection.ssl_domain')
    @patch('gofer.messaging.adapter.amqp.connection.RealConnection')
    def test_open(self, connection, ssl_domain, find):
        url = TEST_URL
        connector = Connector(url)
        connector.ssl.ca_certificate = 'test-ca'
        connector.ssl.client_key = 'test-key'
        connector.ssl.client_certificate = 'test-crt'
        find.return_value = connector

        # test
        c = Connection(url)
        c._ssh = Mock()
        c.open()

        # validation
        ssl_domain.assert_called_once_with(connector)
        connection.assert_called_once_with(
            host=':'.join((connector.host, str(connector.port))),
            virtual_host=connector.virtual_host,
            userid=connector.userid,
            password=connector.password,
            ssl=ssl_domain.return_value,
            confirm_publish=True)

        connection.return_value.connect.assert_called_once_with()
        self.assertEqual(c._impl, connection.return_value)

    def test_open_already(self):
        url = TEST_URL
        c = Connection(url)
        c._impl = Mock()
        c.open()
        self.assertFalse(c._impl.open.called)

    def test_channel(self):
        url = TEST_URL
        c = Connection(url)
        c._impl = Mock()
        ch = c.channel()
        self.assertEqual(ch, c._impl.channel.return_value)

    @patch('gofer.messaging.adapter.model.SSL.validate')
    def test_ssl_domain(self, validate):
        url = TEST_URL

        # test
        b = Connector(url)
        b.ssl.ca_certificate = 'test-ca'
        b.ssl.client_key = 'test-key'
        b.ssl.client_certificate = 'test-crt'
        ssl = Connection.ssl_domain(b)

        # validation
        validate.assert_called_once_with()
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
        b = Connector(url)
        ssl = Connection.ssl_domain(b)

        # validation
        self.assertEqual(
            ssl,
            {
                'ca_certs': None,
                'certfile': None,
                'keyfile': None,
                'cert_reqs': 0
            })

    def test_ssl_not_ssl(self):
        url = 'amqp://elmer:fudd@redhat.com:1234'

        # test
        b = Connector(url)
        ssl = Connection.ssl_domain(b)

        self.assertEqual(str(b.url), url)

        # validation
        self.assertEqual(ssl, None)

    def test_close(self):
        url = 'test-url'
        c = Connection(url)
        impl = Mock()
        c._impl = impl
        c.close()
        impl.close.assert_called_once_with()
        self.assertEqual(c._impl, None)

    def test_close_failed(self):
        url = 'test-url'
        c = Connection(url)
        impl = Mock()
        impl.close.side_effect = ValueError
        c._impl = impl
        c.close()
