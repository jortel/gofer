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

with ipatch('proton'):
    from gofer.messaging.adapter.proton.reliability import reliable


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
    def test_reliable_with_errors(self, sleep):
        url = 'test-url'
        fn = Mock(side_effect=[ConnectionException, 'okay'])
        thing = Mock(url=url, connection=Mock())
        args = (thing, 2, 3)
        kwargs = {'A': 1}

        # test
        wrapped = reliable(fn)
        wrapped(*args, **kwargs)

        # validation
        thing.close.assert_called_once_with()
        thing.connection.close.assert_called_once_with()
        sleep.assert_called_once_with(3)
        thing.open.assert_called_once_with()
        self.assertEqual(
            fn.call_args_list,
            [
                (args, kwargs),
                (args, kwargs),
            ])
