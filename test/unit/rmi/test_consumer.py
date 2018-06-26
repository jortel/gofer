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

from gofer.messaging import Queue, Document
from gofer.rmi.consumer import RequestConsumer


class TestConsumer(TestCase):

    def test_init(self):
        node = Queue()
        plugin = Mock(url='')
        consumer = RequestConsumer(node, plugin)
        self.assertEqual(node, consumer.node)
        self.assertEqual(plugin, consumer.plugin)
        self.assertEqual(consumer.scheduler, plugin.scheduler)

    def test_no_route(self):
        node = Queue()
        plugin = Mock(url='')
        consumer = RequestConsumer(node, plugin)
        consumer.abort = Mock()

        # Test
        thread = consumer.no_route()
        thread.join()

        # Validation
        consumer.abort.assert_called_once_with()
        plugin.reload.assert_called_once_with()

    def test_rejected(self):
        node = Queue()
        plugin = Mock(url='')
        code = '401'
        description = 'failed'
        details = dict(msg='failed')
        document = Document(field='value')
        consumer = RequestConsumer(node, plugin)
        consumer.send = Mock()

        # Test
        consumer.rejected(code, description, document, details)

        # Validation
        consumer.send.assert_called_once_with(
            document,
            'rejected',
            **{
                'code' : code,
                'description': description,
                'details': details,
            }
        )

    @patch('gofer.rmi.consumer.Producer.send')
    def test_send_not_addressed(self, send):
        node = Queue()
        plugin = Mock(url='')
        request = Document(replyto=None)
        status = 'rejected'
        consumer = RequestConsumer(node, plugin)

        # Test
        consumer.send(request, status)

        # Validation
        self.assertFalse(send.called)

    @patch('gofer.rmi.consumer.Producer.send')
    @patch('gofer.rmi.consumer.Producer.close')
    @patch('gofer.rmi.consumer.Producer.open')
    @patch('gofer.rmi.consumer.timestamp')
    def test_send(self, ts, _open, _close, send):
        node = Queue()
        plugin = Mock(url='')
        request = Document(
            sn=1,
            replyto='elmer',
            data=123)
        status = 'rejected'
        details = dict(a=1)
        consumer = RequestConsumer(node, plugin)

        # Test
        consumer.send(request, status, **details)

        # Validation
        _open.assert_called_once_with()
        send.assert_called_once_with(
            request.replyto,
            sn=request.sn,
            data=request.data,
            status=status,
            timestamp=ts.return_value,
            **details)
        _close.assert_called_once_with()

    @patch('gofer.rmi.consumer.Producer.send')
    @patch('gofer.rmi.consumer.Producer.close')
    @patch('gofer.rmi.consumer.Producer.open')
    @patch('gofer.rmi.consumer.timestamp')
    def test_send(self, ts, _open, _close, send):
        send.side_effect = ValueError
        node = Queue()
        plugin = Mock(url='')
        request = Document(
            sn=1,
            replyto='elmer',
            data=123)
        status = 'rejected'
        details = dict(a=1)
        consumer = RequestConsumer(node, plugin)

        # Test
        consumer.send(request, status, **details)

        # Validation
        _open.assert_called_once_with()
        _close.assert_called_once_with()

    def test_dispatch(self):
        node = Queue()
        plugin = Mock(url='')
        request = Document()
        consumer = RequestConsumer(node, plugin)
        consumer.send = Mock()

        # Test
        consumer.dispatch(request)

        # Validation
        consumer.send.assert_called_once_with(request, 'accepted')
        plugin.scheduler.add.assert_called_once_with(request)
