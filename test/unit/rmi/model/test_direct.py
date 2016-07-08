#
# Copyright (c) 2016 Red Hat, Inc.
#
# This software is licensed to you under the GNU Lesser General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (LGPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of LGPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/lgpl-2.0.txt.
#
# Jeff Ortel <jortel@redhat.com>
#

from unittest import TestCase

from mock import Mock

from gofer.rmi.model.direct import Call


class TestCall(TestCase):

    def test_call(self):
        method = Mock()
        args = [1, 2]
        kwargs = {'A': 1}

        # test
        model = Call(method, *args, **kwargs)
        retval = model()

        # validation
        method.assert_called_once_with(*args, **kwargs)
        self.assertEqual(retval, method.return_value)
