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

with ipatch('amqplib'):
    from gofer.messaging import URL
    from gofer.messaging.adapter.amqplib.broker import Broker, BaseBroker, SocketError


class Local(object):
    pass


class TestBroker(TestCase):

    def test_init(self):
        url = 'test-url://'
        b = Broker(url)
        self.assertTrue(isinstance(b, BaseBroker))
        self.assertEqual(b.url, URL(url))

    @patch('gofer.messaging.adapter.amqplib.broker.Broker.open')
    def test_connect(self, _open):
        url = 'test-url://'

        # test
        b = Broker(url)
        b.connection = Local()
        b.connect()

        # validation
        _open.assert_called_once_with()
        self.assertEqual(b.connection.cached, _open.return_value)

    @patch('gofer.messaging.adapter.amqplib.broker.Broker._ssl')
    @patch('gofer.messaging.adapter.amqplib.broker.Connection')
    def test_open(self, connection, _ssl):
        url = 'amqplib+amqplib://elmer:fudd@redhat.com:1234/test-virtual-host'

        # test
        b = Broker(url)
        b.cacert = 'test-ca'
        b.clientkey = 'test-key'
        b.clientcert = 'test-crt'
        b.connection = Local()
        b._ssh = Mock()
        con = b.open()

        # validation
        _ssl.assert_called_once_with()
        connection.assert_called_once_with(
            host=':'.join((b.host, str(b.port))),
            virtual_host=b.virtual_host,
            userid=b.userid,
            password=b.password,
            ssl=_ssl.return_value)

        self.assertEqual(con, connection.return_value)

    @patch('gofer.messaging.adapter.amqplib.broker.sleep')
    @patch('gofer.messaging.adapter.amqplib.broker.Connection')
    def test_open_with_retry(self, connection, sleep):
        url = 'amqplib+amqplib://elmer:fudd@redhat.com:1234/test-virtual-host'
        side_effect = [SocketError, Mock()]

        connection.side_effect = side_effect

        # test
        b = Broker(url)
        b._ssh = Mock()
        con = b.open(delay=10)

        # validation
        sleep.assert_called_once_with(10)
        self.assertEqual(connection.call_count, 2)
        self.assertEqual(con, side_effect[1])

    @patch('gofer.messaging.adapter.amqplib.broker.sleep')
    @patch('gofer.messaging.adapter.amqplib.broker.Connection')
    def test_open_with_no_retry(self, connection, sleep):
        url = 'amqplib+amqplib://elmer:fudd@redhat.com:1234/test-virtual-host'
        side_effect = [SocketError, Mock()]

        connection.side_effect = side_effect

        # test
        b = Broker(url)
        b._ssh = Mock()
        self.assertRaises(SocketError, b.open, retries=0)

        # validation
        self.assertFalse(sleep.called)
        self.assertEqual(connection.call_count, 1)

    def test_close(self):
        url = 'test-url://'
        conn = Mock()
        b = Broker(url)
        # open
        b.connection = Local()
        b.connection.cached = conn
        b.close()
        # open with connection exception
        conn.close.reset_mock()
        b.connection = Local()
        b.connection.cached = conn
        conn.close.side_effect = SocketError
        b.close()
        conn.close.assert_called_once_with()
        conn.close.reset_mock()
        # already closed
        b.connection = Local()
        b.close()

    def test_ssl(self):
        url = 'amqps://elmer:fudd@redhat.com:1234'

        # test
        b = Broker(url)
        b.cacert = 'test-ca'
        b.clientkey = 'test-key'
        b.clientcert = 'test-crt'
        ssl = b._ssl()

        self.assertEqual(b.url.input, url)

        # validation
        self.assertEqual(
            ssl,
            {
                'ca_certs': b.cacert,
                'cert_reqs': 2,
                'certfile': b.clientcert,
                'keyfile': b.clientkey
            })

    def test_ssl_no_certs(self):
        url = 'amqps://elmer:fudd@redhat.com:1234'

        # test
        b = Broker(url)
        b.cacert = None
        ssl = b._ssl()

        # validation
        self.assertEqual(
            ssl,
            {
                'ca_certs': b.cacert,
                'cert_reqs': 0,
                'certfile': b.clientcert,
                'keyfile': b.clientkey
            })