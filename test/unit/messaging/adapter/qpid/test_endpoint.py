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

from mock import Mock, patch

from gofer.devel import ipatch

with ipatch('qpid.messaging'):
    from gofer.messaging.adapter.qpid.endpoint import Endpoint, BaseEndpoint


class TestEndpoint(TestCase):

    @patch('gofer.messaging.adapter.qpid.endpoint.atexit')
    @patch('gofer.messaging.adapter.qpid.endpoint.RLock')
    def test_init(self, rlock, atexit):
        url = 'test-url'

        # test
        endpoint = Endpoint(url)

        # validation
        atexit.register.assert_called_once_with(endpoint.close)
        self.assertTrue(isinstance(endpoint, BaseEndpoint))
        self.assertEqual(endpoint._Endpoint__mutex, rlock.return_value)
        self.assertEqual(endpoint._Endpoint__session, None)
        self.assertEqual(endpoint.url, url)

    @patch('gofer.messaging.adapter.qpid.endpoint.Broker')
    @patch('gofer.messaging.adapter.qpid.endpoint.atexit', Mock())
    @patch('gofer.messaging.adapter.qpid.endpoint.RLock', Mock())
    def test_channel(self, broker):
        url = 'test-url'
        connection = Mock()
        broker.return_value.connect.return_value = connection

        # test
        endpoint = Endpoint(url)
        channel = endpoint.channel()

        # validation
        broker.assert_called_once_with(url)
        connection.session.assert_called_once_with()
        self.assertEqual(channel, connection.session.return_value)
        self.assertEqual(channel, endpoint._Endpoint__session)

    @patch('gofer.messaging.adapter.qpid.endpoint.Broker')
    @patch('gofer.messaging.adapter.qpid.endpoint.atexit', Mock())
    @patch('gofer.messaging.adapter.qpid.endpoint.RLock', Mock())
    def test_channel_cached(self, broker):
        url = 'test-url'

        # test
        endpoint = Endpoint(url)
        endpoint._Endpoint__session = Mock()
        channel = endpoint.channel()

        # validation
        self.assertEqual(channel, endpoint._Endpoint__session)
        self.assertFalse(broker.called)

    @patch('gofer.messaging.adapter.qpid.endpoint.atexit', Mock())
    @patch('gofer.messaging.adapter.qpid.endpoint.RLock', Mock())
    def test_ack(self):
        url = 'test-url'
        message = Mock()

        # test
        endpoint = Endpoint(url)
        endpoint._Endpoint__session = Mock()
        endpoint.ack(message)

        # validation
        endpoint._Endpoint__session.acknowledge.assert_called_once_with(message=message)

    @patch('gofer.messaging.adapter.qpid.endpoint.atexit', Mock())
    @patch('gofer.messaging.adapter.qpid.endpoint.RLock', Mock())
    def test_ack_exception(self):
        url = 'test-url'
        message = Mock()
        session = Mock()
        session.acknowledge.side_effect = ValueError

        # test
        endpoint = Endpoint(url)
        endpoint._Endpoint__session = session
        endpoint.ack(message)

        # validation
        session.acknowledge.assert_called_once_with(message=message)

    @patch('gofer.messaging.adapter.qpid.endpoint.RELEASED')
    @patch('gofer.messaging.adapter.qpid.endpoint.Disposition')
    @patch('gofer.messaging.adapter.qpid.endpoint.atexit', Mock())
    @patch('gofer.messaging.adapter.qpid.endpoint.RLock', Mock())
    def test_reject_released(self, disposition, released):
        url = 'test-url'
        message = Mock()

        # test
        endpoint = Endpoint(url)
        endpoint._Endpoint__session = Mock()
        endpoint.reject(message)

        # validation
        disposition.assert_called_once_with(released)
        endpoint._Endpoint__session.acknowledge.assert_called_once_with(
            message=message, disposition=disposition.return_value)

    @patch('gofer.messaging.adapter.qpid.endpoint.Disposition')
    @patch('gofer.messaging.adapter.qpid.endpoint.atexit', Mock())
    @patch('gofer.messaging.adapter.qpid.endpoint.RLock', Mock())
    def test_reject_exception(self, disposition):
        url = 'test-url'
        message = Mock()
        session = Mock()
        session.acknowledge.side_effect = ValueError

        # test
        endpoint = Endpoint(url)
        endpoint._Endpoint__session = session
        endpoint.reject(message)

        # validation
        endpoint._Endpoint__session.acknowledge.assert_called_once_with(
            message=message, disposition=disposition.return_value)


    @patch('gofer.messaging.adapter.qpid.endpoint.REJECTED')
    @patch('gofer.messaging.adapter.qpid.endpoint.Disposition')
    @patch('gofer.messaging.adapter.qpid.endpoint.atexit', Mock())
    @patch('gofer.messaging.adapter.qpid.endpoint.RLock', Mock())
    def test_reject_rejected(self, disposition, rejected):
        url = 'test-url'
        message = Mock()

        # test
        endpoint = Endpoint(url)
        endpoint._Endpoint__session = Mock()
        endpoint.reject(message, requeue=False)

        # validation
        disposition.assert_called_once_with(rejected)
        endpoint._Endpoint__session.acknowledge.assert_called_once_with(
            message=message, disposition=disposition.return_value)

    @patch('gofer.messaging.adapter.qpid.endpoint.atexit', Mock())
    @patch('gofer.messaging.adapter.qpid.endpoint.RLock', Mock())
    def test_open(self):
        endpoint = Endpoint('')
        endpoint.open()

    @patch('gofer.messaging.adapter.qpid.endpoint.atexit', Mock())
    @patch('gofer.messaging.adapter.qpid.endpoint.RLock', Mock())
    def test_close(self):
        session = Mock()

        # test
        endpoint = Endpoint('')
        endpoint._Endpoint__session = session
        endpoint.close()

        # validation
        session.close.assert_called_once_with()
        self.assertEqual(endpoint._Endpoint__session, None)

    @patch('gofer.messaging.adapter.qpid.endpoint.atexit', Mock())
    @patch('gofer.messaging.adapter.qpid.endpoint.RLock', Mock())
    def test_close_no_session(self):
        session = Mock()

        # test
        endpoint = Endpoint('')
        endpoint.close()

        # validation
        self.assertFalse(session.close.called)

    @patch('gofer.messaging.adapter.qpid.endpoint.RLock')
    @patch('gofer.messaging.adapter.qpid.endpoint.atexit', Mock())
    def test_lock(self, lock):
        endpoint = Endpoint('')
        endpoint._lock()
        lock.return_value.acquire.assert_called_once_with()

    @patch('gofer.messaging.adapter.qpid.endpoint.RLock')
    @patch('gofer.messaging.adapter.qpid.endpoint.atexit', Mock())
    def test_unlock(self, lock):
        endpoint = Endpoint('')
        endpoint._unlock()
        lock.return_value.release.assert_called_once_with()

    @patch('gofer.messaging.adapter.qpid.endpoint.atexit', Mock())
    @patch('gofer.messaging.adapter.qpid.endpoint.RLock', Mock())
    def test_del(self):
        endpoint = Endpoint('')
        endpoint.close = Mock()
        endpoint.__del__()
        endpoint.close.assert_called_once_with()

    @patch('gofer.messaging.adapter.qpid.endpoint.atexit', Mock())
    @patch('gofer.messaging.adapter.qpid.endpoint.RLock', Mock())
    def test_del_exception(self):
        endpoint = Endpoint('')
        endpoint.close = Mock(side_effect=ValueError)
        endpoint.__del__()
        endpoint.close.assert_called_once_with()

    @patch('gofer.messaging.adapter.qpid.endpoint.RLock', Mock())
    @patch('gofer.messaging.adapter.qpid.endpoint.atexit', Mock())
    def test_str(self):
        endpoint = Endpoint('test-url')
        endpoint.uuid = 'test-uuid'
        self.assertEqual(str(endpoint), 'Endpoint id:test-uuid broker @ test-url')

    @patch('gofer.messaging.adapter.qpid.endpoint.atexit', Mock())
    @patch('gofer.messaging.adapter.qpid.endpoint.RLock', Mock())
    def test_enter(self):
        endpoint = Endpoint('')
        endpoint.open = Mock()
        obj = endpoint.__enter__()
        endpoint.open.assert_called_once_with()
        self.assertEqual(obj, endpoint)

    @patch('gofer.messaging.adapter.qpid.endpoint.atexit', Mock())
    @patch('gofer.messaging.adapter.qpid.endpoint.RLock', Mock())
    def test_exit(self):
        endpoint = Endpoint('')
        endpoint.close = Mock()
        endpoint.__exit__()
        endpoint.close.assert_called_once_with()
