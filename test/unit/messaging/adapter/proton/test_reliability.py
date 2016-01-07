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
    from gofer.messaging.adapter.proton.reliability import reliable
    from gofer.messaging.adapter.proton.reliability import DELAY


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
        messenger = Mock()
        args = (messenger, 2, 3)
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
        messenger = Mock(url=url, connection=Mock())
        args = (messenger, 2, 3)
        kwargs = {'A': 1}

        # test
        wrapped = reliable(fn)
        wrapped(*args, **kwargs)

        # validation
        sleep.assert_called_once_with(DELAY)
        messenger.repair.assert_called_once_with()
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
        messenger = Mock(url=url, connection=Mock())
        args = (messenger, 2, 3)
        kwargs = {'A': 1}

        # test
        wrapped = reliable(fn)
        wrapped(*args, **kwargs)

        # validation
        sleep.assert_called_once_with(DELAY)
        messenger.repair.assert_called_once_with()
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
