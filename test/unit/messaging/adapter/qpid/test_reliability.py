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

with ipatch('qpid'):
    from gofer.messaging.adapter.qpid.reliability import reliable


class _NotFound(Exception):
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

    @patch('gofer.messaging.adapter.qpid.reliability._NotFound', _NotFound)
    def test_reliable_not_found(self):
        url = 'test-url'
        fn = Mock(side_effect=[ValueError, None])
        thing = Mock(url=url, connection=Mock())
        args = (thing, 2, 3)
        kwargs = {'A': 1}

        # test
        wrapped = reliable(fn)
        self.assertRaises(ValueError, wrapped, *args, **kwargs)

    @patch('gofer.messaging.adapter.qpid.reliability._NotFound', _NotFound)
    def test_reliable_not_found(self):
        url = 'test-url'
        fn = Mock(side_effect=[_NotFound, None])
        thing = Mock(url=url, connection=Mock())
        args = (thing, 2, 3)
        kwargs = {'A': 1}

        # test
        wrapped = reliable(fn)
        self.assertRaises(NotFound, wrapped, *args, **kwargs)
