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

from mock import Mock, patch

from gofer.devel import ipatch

from gofer.messaging.adapter.model import NotFound

with ipatch('proton'):
    from gofer.messaging.adapter.proton.reliability import reliable, resend
    from gofer.messaging.adapter.proton.reliability import DELAY, RESEND_DELAY


class LinkDetached(Exception):

    def __init__(self, condition=None):
        self.condition = condition


class SendException(Exception):

    def __init__(self, state=0):
        self.state = state


class ConnectionException(Exception):
    pass


class TestReliable(TestCase):

    def test_reliable(self):
        fn = Mock()
        thing = Mock()
        args = (thing, 2, 3)
        kwargs = {'A': 1}

        # test
        wrapped = reliable(fn)
        wrapped(*args, **kwargs)

        # validation
        fn.assert_called_once_with(*args, **kwargs)

    @patch('gofer.messaging.adapter.proton.reliability.ConnectionException', ConnectionException)
    @patch('gofer.messaging.adapter.proton.reliability.sleep')
    def test_reliable_connection_exception(self, sleep):
        url = 'test-url'
        fn = Mock(side_effect=[ConnectionException, None])
        thing = Mock(url=url, connection=Mock())
        args = (thing, 2, 3)
        kwargs = {'A': 1}

        # test
        wrapped = reliable(fn)
        wrapped(*args, **kwargs)

        # validation
        sleep.assert_called_once_with(DELAY)
        thing.repair.assert_called_once_with()
        self.assertEqual(
            fn.call_args_list,
            [
                (args, kwargs),
                (args, kwargs),
            ])

    @patch('gofer.messaging.adapter.proton.reliability.LinkDetached', LinkDetached)
    @patch('gofer.messaging.adapter.proton.reliability.sleep')
    def test_reliable_link_detached(self, sleep):
        url = 'test-url'
        fn = Mock(side_effect=[LinkDetached, None])
        thing = Mock(url=url, connection=Mock())
        args = (thing, 2, 3)
        kwargs = {'A': 1}

        # test
        wrapped = reliable(fn)
        wrapped(*args, **kwargs)

        # validation
        sleep.assert_called_once_with(DELAY)
        thing.repair.assert_called_once_with()
        self.assertEqual(
            fn.call_args_list,
            [
                (args, kwargs),
                (args, kwargs),
            ])

    @patch('gofer.messaging.adapter.proton.reliability.LinkDetached', LinkDetached)
    @patch('gofer.messaging.adapter.proton.reliability.sleep')
    def test_reliable_link_not_found(self, sleep):
        url = 'test-url'
        condition = 'amqp:not-found'
        fn = Mock(side_effect=LinkDetached(condition))

        # test
        wrapped = reliable(fn)
        self.assertRaises(NotFound, wrapped, None)
        self.assertFalse(sleep.called)


class TestResend(TestCase):

    @patch('gofer.messaging.adapter.proton.reliability.Delivery')
    @patch('gofer.messaging.adapter.proton.reliability.SendException', SendException)
    @patch('gofer.messaging.adapter.proton.reliability.sleep')
    def test_resend_released(self, sleep, delivery):
        url = 'test-url'
        delivery.RELEASED = 1
        fn = Mock(side_effect=[SendException(delivery.RELEASED), None])
        thing = Mock(url=url, connection=Mock())
        args = (thing, 2, 3)
        kwargs = {'A': 1}

        # test
        wrapped = resend(fn)
        wrapped(*args, **kwargs)

        # validation
        sleep.assert_called_once_with(RESEND_DELAY)
        self.assertEqual(
            fn.call_args_list,
            [
                (args, kwargs),
                (args, kwargs),
            ])

    @patch('gofer.messaging.adapter.proton.reliability.Delivery')
    @patch('gofer.messaging.adapter.proton.reliability.SendException', SendException)
    @patch('gofer.messaging.adapter.proton.reliability.sleep')
    def test_resend_rejected(self, sleep, delivery):
        url = 'test-url'
        delivery.RELEASED = 1
        delivery.REJECTED = 2
        fn = Mock(side_effect=[SendException(delivery.REJECTED), None])
        thing = Mock(url=url, connection=Mock())
        args = (thing, 2, 3)
        kwargs = {'A': 1}

        # test
        wrapped = resend(fn)
        self.assertRaises(SendException, wrapped, *args, **kwargs)
        self.assertFalse(sleep.called)

    @patch('gofer.messaging.adapter.proton.reliability.Delivery')
    @patch('gofer.messaging.adapter.proton.reliability.MAX_RESEND', 4)
    @patch('gofer.messaging.adapter.proton.reliability.SendException', SendException)
    @patch('gofer.messaging.adapter.proton.reliability.sleep')
    def test_resend_exhausted(self, sleep, delivery):
        url = 'test-url'
        delivery.RELEASED = 1
        fn = Mock(side_effect=SendException(delivery.RELEASED))
        thing = Mock(url=url, connection=Mock())
        args = (thing, 2, 3)
        kwargs = {'A': 1}

        # test
        wrapped = resend(fn)
        wrapped(*args, **kwargs)

        # validation
        self.assertEqual(
            sleep.call_args_list,
            [
                ((RESEND_DELAY,), {}),
                ((RESEND_DELAY,), {}),
                ((RESEND_DELAY,), {}),
                ((RESEND_DELAY,), {}),
            ])
        self.assertEqual(
            fn.call_args_list,
            [
                (args, kwargs),
                (args, kwargs),
                (args, kwargs),
                (args, kwargs),
            ])
