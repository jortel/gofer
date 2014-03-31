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

from gofer.transport.broker import MetaBroker, Broker, URL


class TestURL(TestCase):

    def test_url(self):
        transport = 'amqp'
        host = 'redhat'
        port = 1234

        # test
        url = URL('%s://%s:%d' % (transport, host, port))

        # validation
        self.assertEqual(url.transport, transport)
        self.assertEqual(url.host, host)
        self.assertEqual(url.port, port)
        self.assertEqual(url.userid, None)
        self.assertEqual(url.password, None)

    def test_url_host_only(self):
        transport = 'amqp'
        host = 'redhat'

        # test
        url = URL('%s://%s' % (transport, host))

        # validation
        self.assertEqual(url.transport, transport)
        self.assertEqual(url.host, host)
        self.assertEqual(url.port, 5672)
        self.assertEqual(url.userid, None)
        self.assertEqual(url.password, None)

    def test_url_no_transport(self):
        host = 'redhat'

        # test
        url = URL(host)

        # validation
        self.assertEqual(url.transport, 'amqp')
        self.assertEqual(url.host, host)
        self.assertEqual(url.port, 5672)
        self.assertEqual(url.userid, None)
        self.assertEqual(url.password, None)

    def test_userid_and_password(self):
        transport = 'amqp'
        host = 'redhat'
        port = 1234
        userid = 'elmer'
        password = 'fudd'

        # test
        url = URL('%s/%s@%s://%s:%d' % (userid, password, transport, host, port))

        # validation
        self.assertEqual(url.transport, transport)
        self.assertEqual(url.host, host)
        self.assertEqual(url.port, port)
        self.assertEqual(url.userid, userid)
        self.assertEqual(url.password, password)


class TestBroker(TestCase):

    def setUp(self):
        MetaBroker.reset()

    def test_url(self):
        transport = 'amqp'
        host = 'redhat'
        port = 1234

        # test
        url = URL('%s://%s:%d' % (transport, host, port))
        broker = Broker(url)

        # validation
        self.assertEqual(broker.transport, transport)
        self.assertEqual(broker.host, host)
        self.assertEqual(broker.port, port)
        self.assertEqual(broker.userid, None)
        self.assertEqual(broker.password, None)

    def test_url_host_only(self):
        transport = 'amqp'
        host = 'redhat'

        # test
        url = URL('%s://%s' % (transport, host))
        broker = Broker(url)

        # validation
        self.assertEqual(broker.transport, transport)
        self.assertEqual(broker.host, host)
        self.assertEqual(broker.port, 5672)
        self.assertEqual(broker.userid, None)
        self.assertEqual(broker.password, None)

    def test_url_no_transport(self):
        host = 'redhat'

        # test
        url = URL(host)
        broker = Broker(url)

        # validation
        self.assertEqual(broker.transport, 'amqp')
        self.assertEqual(broker.host, host)
        self.assertEqual(broker.port, 5672)
        self.assertEqual(broker.userid, None)
        self.assertEqual(broker.password, None)

    def test_userid_and_password(self):
        transport = 'amqp'
        host = 'redhat'
        port = 1234
        userid = 'elmer'
        password = 'fudd'

        # test
        url = URL('%s/%s@%s://%s:%d' % (userid, password, transport, host, port))
        broker = Broker(url)

        # validation
        self.assertEqual(broker.transport, transport)
        self.assertEqual(broker.host, host)
        self.assertEqual(broker.port, port)
        self.assertEqual(broker.userid, userid)
        self.assertEqual(broker.password, password)