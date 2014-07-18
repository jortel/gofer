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
        transport = 'qpid'
        scheme = 'amqp'
        host = 'redhat'
        port = 1234
        path = '/'

        # test
        url = URL('%s+%s://%s:%d%s/' % (transport, scheme, host, port, path))

        # validation
        self.assertEqual(url.transport, transport)
        self.assertEqual(url.scheme, scheme)
        self.assertEqual(url.host, host)
        self.assertEqual(url.port, port)
        self.assertEqual(url.userid, None)
        self.assertEqual(url.password, None)
        self.assertEqual(url.path, path)

    def test_url_long_path(self):
        scheme = 'amqp'
        host = 'redhat'
        port = 1234
        path = 'a/b/c/'

        # test
        url = URL('%s://%s:%d/%s' % (scheme, host, port, path))

        # validation
        self.assertEqual(url.transport, None)
        self.assertEqual(url.scheme, scheme)
        self.assertEqual(url.host, host)
        self.assertEqual(url.port, port)
        self.assertEqual(url.userid, None)
        self.assertEqual(url.password, None)
        self.assertEqual(url.path, path)

    def test_url_empty_path(self):
        scheme = 'amqp'
        host = 'redhat'
        port = 1234

        # test
        url = URL('%s://%s:%d/' % (scheme, host, port))

        # validation
        self.assertEqual(url.scheme, scheme)
        self.assertEqual(url.host, host)
        self.assertEqual(url.port, port)
        self.assertEqual(url.userid, None)
        self.assertEqual(url.password, None)
        self.assertEqual(url.path, '')

    def test_url_no_path(self):
        scheme = 'amqp'
        host = 'redhat'
        port = 1234

        # test
        url = URL('%s://%s:%d' % (scheme, host, port))

        # validation
        self.assertEqual(url.scheme, scheme)
        self.assertEqual(url.host, host)
        self.assertEqual(url.port, port)
        self.assertEqual(url.userid, None)
        self.assertEqual(url.password, None)
        self.assertEqual(url.path, None)

    def test_url_host_only(self):
        scheme = 'amqp'
        host = 'redhat'

        # test
        url = URL('%s://%s' % (scheme, host))

        # validation
        self.assertEqual(url.scheme, scheme)
        self.assertEqual(url.host, host)
        self.assertEqual(url.port, 5672)
        self.assertEqual(url.userid, None)
        self.assertEqual(url.password, None)
        self.assertEqual(url.path, None)

    def test_url_no_scheme(self):
        host = 'redhat'

        # test
        url = URL(host)

        # validation
        self.assertEqual(url.scheme, 'amqp')
        self.assertEqual(url.host, host)
        self.assertEqual(url.port, 5672)
        self.assertEqual(url.userid, None)
        self.assertEqual(url.password, None)
        self.assertEqual(url.path, None)

    def test_userid_and_password(self):
        scheme = 'amqp'
        host = 'redhat'
        port = 1234
        userid = 'elmer'
        password = 'fudd'

        # test
        url = URL('%s://%s:%s@%s:%d' % (scheme, userid, password, host, port))

        # validation
        self.assertEqual(url.scheme, scheme)
        self.assertEqual(url.host, host)
        self.assertEqual(url.port, port)
        self.assertEqual(url.userid, userid)
        self.assertEqual(url.password, password)
        self.assertEqual(url.path, None)


class TestBroker(TestCase):

    def setUp(self):
        MetaBroker.reset()

    def test_url(self):
        scheme = 'amqp'
        host = 'redhat'
        port = 1234

        # test
        url = URL('%s://%s:%d' % (scheme, host, port))
        broker = Broker(url)

        # validation
        self.assertEqual(broker.scheme, scheme)
        self.assertEqual(broker.host, host)
        self.assertEqual(broker.port, port)
        self.assertEqual(broker.userid, None)
        self.assertEqual(broker.password, None)
        self.assertEqual(broker.virtual_host, None)

    def test_url_host_only(self):
        scheme = 'amqp'
        host = 'redhat'

        # test
        url = URL('%s://%s' % (scheme, host))
        broker = Broker(url)

        # validation
        self.assertEqual(broker.scheme, scheme)
        self.assertEqual(broker.host, host)
        self.assertEqual(broker.port, 5672)
        self.assertEqual(broker.userid, None)
        self.assertEqual(broker.password, None)
        self.assertEqual(broker.virtual_host, None)

    def test_url_no_scheme(self):
        host = 'redhat'

        # test
        url = URL(host)
        broker = Broker(url)

        # validation
        self.assertEqual(broker.scheme, 'amqp')
        self.assertEqual(broker.host, host)
        self.assertEqual(broker.port, 5672)
        self.assertEqual(broker.userid, None)
        self.assertEqual(broker.password, None)
        self.assertEqual(broker.virtual_host, None)

    def test_userid_and_password(self):
        scheme = 'amqp'
        host = 'redhat'
        port = 1234
        userid = 'elmer'
        password = 'fudd'

        # test
        url = URL('%s://%s:%s@%s:%d' % (scheme, userid, password, host, port))
        broker = Broker(url)

        # validation
        self.assertEqual(broker.scheme, scheme)
        self.assertEqual(broker.host, host)
        self.assertEqual(broker.port, port)
        self.assertEqual(broker.userid, userid)
        self.assertEqual(broker.password, password)
        self.assertEqual(broker.virtual_host, None)

    def test_userid_and_no_password(self):
        scheme = 'amqp'
        host = 'redhat'
        port = 1234

        # test
        url = URL('%s://elmer@%s:%d/' % (scheme, host, port))
        broker = Broker(url)

        # validation
        self.assertEqual(broker.scheme, scheme)
        self.assertEqual(broker.host, host)
        self.assertEqual(broker.port, port)
        self.assertEqual(broker.userid, None)
        self.assertEqual(broker.password, None)
        self.assertEqual(broker.virtual_host, '')

    def test_userid_and_password_no_port(self):
        scheme = 'amqp'
        host = 'redhat'
        userid = 'elmer'
        password = 'fudd'

        # test
        url = URL('%s://%s:%s@%s' % (scheme, userid, password, host))
        broker = Broker(url)

        # validation
        self.assertEqual(broker.scheme, scheme)
        self.assertEqual(broker.host, host)
        self.assertEqual(broker.port, 5672)
        self.assertEqual(broker.userid, userid)
        self.assertEqual(broker.password, password)
        self.assertEqual(broker.virtual_host, None)
