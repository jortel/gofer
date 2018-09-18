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


class Thing(object):

    def __init__(self, n1, n2, a=0, b=0):
        super(Thing, self).__init__()
        self.name = 'Elmer' + chr(255) + 'Fudd'
        self.n1 = n1
        self.n2 = n2
        self.a = a
        self.b = b

    def __str__(self):
        return str(self.name)


class TestStrings(TestCase):

    def test_str(self):
        self.assertTrue(isinstance(str('hello'), str))
