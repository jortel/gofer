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
from gofer import Singleton

with ipatch('qpid.messaging'):
    from gofer.messaging import URL
    from gofer.messaging.adapter.qpid.broker import Broker, BaseBroker


class Local(object):
    pass


class TestBroker(TestCase):

    def setUp(self):
        Singleton._Singleton__inst = {}

    def tearDown(self):
        Singleton._Singleton__inst = {}

    def test_init(self):
        url = 'test-url://'
        b = Broker(url)
        self.assertTrue(isinstance(b, BaseBroker))
        self.assertEqual(b.url, URL(url))

    def test_add_transports(self):
        transports = {
            'tcp': Mock(),
            'ssl': Mock()
        }
        with patch('gofer.messaging.adapter.qpid.broker.TRANSPORTS', transports):
            Broker.add_transports()
            self.assertEqual(transports['amqp'], transports['tcp'])
            self.assertEqual(transports['amqps'], transports['ssl'])

    @patch('gofer.messaging.adapter.qpid.broker.Connection')
    @patch('gofer.messaging.adapter.qpid.broker.Broker.add_transports')
    def test_connect(self, add_transports, connection):
        url = 'qpid+amqp://elmer:fudd@redhat.com:1234'
        b = Broker(url)
        b.cacert = 'test-ca'
        b.clientkey = 'test-key'
        b.clientcert = 'test-crt'
        b.connection = Local()

        # test
        con = b.connect()

        # validation
        add_transports.assert_called_once_with()
        connection.assert_called_once_with(
            host=b.host,
            port=b.port,
            tcp_nodelay=True,
            reconnect=True,
            transport=b.scheme,
            username=b.userid,
            password=b.password,
            ssl_trustfile=b.cacert,
            ssl_keyfile=b.clientkey,
            ssl_certfile=b.clientcert,
            ssl_skip_hostname_check=(not b.host_validation))

        con.attach.assert_called_once_with()
        self.assertEqual(b.connection.cached, connection.return_value)
        self.assertEqual(con, connection.return_value)

    def test_close(self):
        url = 'test-url://'
        conn = Mock()
        b = Broker(url)
        # open
        b.connection = Local()
        b.connection.cached = conn
        b.close()
        conn.close.assert_called_once_with()
        # already closed
        b.connection = Local()
        b.close()
