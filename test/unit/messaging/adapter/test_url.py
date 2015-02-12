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

from gofer.messaging.adapter.url import URL


class Test(object):

    def __init__(self,
                 url,
                 adapter=None,
                 scheme=None,
                 host=None,
                 port=None,
                 userid=None,
                 password=None,
                 path=None):
        self.url = url
        self.adapter = adapter
        self.scheme = scheme
        self.host = host
        self.port = port
        self.userid = userid
        self.password = password
        self.path = path

    def __call__(self, test):
        url = URL(self.url)
        test.assertEqual(url.adapter, self.adapter)
        test.assertEqual(url.scheme, self.scheme)
        test.assertEqual(url.host, self.host)
        test.assertEqual(url.port, self.port)
        test.assertEqual(url.userid, self.userid)
        test.assertEqual(url.password, self.password)
        test.assertEqual(url.path, self.path)


TESTS = [
    Test('qpid+amqp://elmer:fudd@blue:5000/all',
         adapter='qpid',
         scheme='amqp',
         host='blue',
         port=5000,
         userid='elmer',
         password='fudd',
         path='all'),
    Test('amqp://elmer:fudd@yellow:1234//',
         scheme='amqp',
         host='yellow',
         port=1234,
         userid='elmer',
         password='fudd',
         path='/'),
    Test('amqp://green:5678/all/good',
         scheme='amqp',
         host='green',
         port=5678,
         path='all/good'),
    Test('amqp://red:2323',
         scheme='amqp',
         host='red',
         port=2323),
    Test('amqp://black',
         scheme='amqp',
         host='black',
         port=5672),
    Test('amqps://purple',
         scheme='amqps',
         host='purple',
         port=5671),
    Test('orange:6545',
         scheme='amqp',
         host='orange',
         port=6545),
    Test('localhost',
         scheme='amqp',
         host='localhost',
         port=5672),
    Test('',
         scheme='amqp',
         port=5672),
]


class TestURL(TestCase):

    def test_parsing(self):
        for test in TESTS:
            test(self)

    def test_domain_id(self):
        urls = [
            'qpid+amqp://elmer:fudd@test-host:5000/all',
            'amqp://elmer:fudd@test-host:5000/all',
            'amqp://test-host:5000/all',
            'amqp://test-host:5000'
        ]
        for _url in urls:
            url = URL(_url)
            self.assertEqual(url.domain_id, 'test-host:5000')

    def test_standard(self):
        urls = [
            'qpid+amqp://elmer:fudd@test-host:5000/all',
            'amqp://elmer:fudd@test-host:5000/all',
            'amqp://test-host:5000/all',
            'amqp://test-host:5000'
        ]
        for _url in urls:
            url = URL(_url)
            self.assertEqual(url.standard(), _url.split('+')[-1].rsplit('/all')[0])

    def test_is_ssl(self):
        # false
        url = URL('amqp://localhost')
        self.assertFalse(url.is_ssl())
        # true
        url = URL('amqps://localhost')
        self.assertTrue(url.is_ssl())
        # true w/ explict port
        url = URL('amqp://localhost:5671')
        self.assertTrue(url.is_ssl())

    def test_hash(self):
        url = URL('test')
        self.assertEqual(hash(url), hash(url.domain_id))

    def test_str(self):
        urls = [
            'qpid+amqp://elmer:fudd@test-host:5000/all',
            'amqp://elmer:fudd@test-host:5000/all',
            'amqp://test-host:5000/all',
            'amqp://test-host:5000',
            'amqp://test-host',
        ]
        for _url in urls:
            url = URL(_url)
            self.assertEqual(str(url), url.standard())

