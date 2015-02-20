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

with ipatch('qpid'):
    from gofer.messaging.adapter.model import Connector
    from gofer.messaging.adapter.qpid.connection import Connection, BaseConnection


TEST_URL = 'amqp+amqps://elmer:fudd@redhat.com:1234/test-virtual-host'


class Local(object):
    pass


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

    def test_add_transports(self):
        transports = {
            'tcp': Mock(),
            'ssl': Mock()
        }
        with patch('gofer.messaging.adapter.qpid.connection.TRANSPORTS', transports):
            Connection.add_transports()
            self.assertEqual(transports['amqp'], transports['tcp'])
            self.assertEqual(transports['amqps'], transports['ssl'])

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
                'ssl_trustfile': b.ssl.ca_certificate,
                'ssl_keyfile': b.ssl.client_key,
                'ssl_certfile': b.ssl.client_certificate,
                'ssl_skip_hostname_check': (not b.ssl.host_validation)
            })

    @patch('gofer.messaging.adapter.qpid.connection.Connection.ssl_domain')
    @patch('gofer.messaging.adapter.qpid.connection.Connection.add_transports')
    @patch('gofer.messaging.adapter.qpid.connection.Connector.find')
    @patch('gofer.messaging.adapter.qpid.connection.RealConnection')
    def test_open(self, connection, find, add_transports, ssl_domain):
        url = TEST_URL
        connector = Connector(url)
        connector.ssl.ca_certificate = 'test-ca'
        connector.ssl.client_key = 'test-key'
        connector.ssl.client_certificate = 'test-crt'
        find.return_value = connector

        ssl_properties = {'A': 1, 'B': 2}
        ssl_domain.return_value = ssl_properties

        # test
        c = Connection(url)
        c._ssh = Mock()
        c.open()

        # validation
        add_transports.assert_called_once_with()
        connection.assert_called_once_with(
            host=connector.host,
            port=connector.port,
            tcp_nodelay=True,
            reconnect=True,
            transport=connector.scheme,
            username=connector.userid,
            password=connector.password,
            heartbeat=10,
            **ssl_properties)

        ssl_domain.assert_called_once_with(connector)
        c._impl.attach.assert_called_once_with()
        self.assertEqual(c._impl, connection.return_value)

    def test_open_already(self):
        url = TEST_URL
        c = Connection(url)
        c._impl = Mock()
        c.open()
        self.assertFalse(c._impl.open.called)

    def test_session(self):
        url = TEST_URL
        c = Connection(url)
        c._impl = Mock()
        session = c.session()
        self.assertEqual(session, c._impl.session.return_value)

    def test_close(self):
        url = TEST_URL
        c = Connection(url)
        impl = Mock()
        c._impl = impl
        c.close()
        impl.close.assert_called_once_with()
        self.assertEqual(c._impl, None)
