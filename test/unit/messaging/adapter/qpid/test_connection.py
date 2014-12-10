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

with ipatch('qpid.messaging'):
    from gofer.messaging.adapter.model import Broker
    from gofer.messaging.adapter.qpid.connection import Connection, BaseConnection


TEST_URL = 'amqp+amqps://elmer:fudd@redhat.com:1234/test-virtual-host'


class Local(object):
    pass


class TestConnection(TestCase):

    def setUp(self):
        Connection.local.d = {}

    def tearDown(self):
        Connection.local.d = {}

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

    @patch('gofer.messaging.adapter.qpid.connection.Connection.add_transports')
    @patch('gofer.messaging.adapter.qpid.connection.Domain.broker.find')
    @patch('gofer.messaging.adapter.qpid.connection.RealConnection')
    def test_open(self, connection, find, add_transports):
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
        add_transports.assert_called_once_with()
        connection.assert_called_once_with(
            host=broker.host,
            port=broker.port,
            tcp_nodelay=True,
            reconnect=True,
            transport=broker.scheme,
            username=broker.userid,
            password=broker.password,
            ssl_trustfile=broker.ssl.ca_certificate,
            ssl_keyfile=broker.ssl.client_key,
            ssl_certfile=broker.ssl.client_certificate,
            ssl_skip_hostname_check=(not broker.ssl.host_validation))

        c._impl.attach.assert_called_once_with()
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
        self.assertEqual(ch, c._impl.session.return_value)

    def test_close(self):
        url = TEST_URL
        c = Connection(url)
        # soft
        impl = Mock()
        c._impl = impl
        c.close()
        self.assertFalse(impl.close.called)
        # hard
        impl = Mock()
        c._impl = impl
        c.close(True)
        impl.close.assert_called_once_with()
        self.assertEqual(c._impl, None)
        # not open
        c._impl = None
        c.close()

    def test_disconnect(self):
        url = TEST_URL
        c = Connection(url)
        c._impl = Mock()
        c._disconnect()
        c._impl.close.assert_called_with()

    def test_disconnect_exception(self):
        url = TEST_URL
        c = Connection(url)
        c._impl = Mock()
        c._impl.close.side_effect = ValueError
        c._disconnect()
        c._impl.close.assert_called_with()
