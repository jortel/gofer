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

import os

from time import sleep
from unittest import TestCase
from tempfile import mktemp

from mock import Mock

from gofer.pmon import PathMonitor


class LiveTest(TestCase):

    def setUp(self):
        self.path = mktemp()

    def tearDown(self):
        if os.path.exists(self.path):
            os.unlink(self.path)

    def test_changed(self):
        function = Mock()
        fp = open(self.path, 'w')
        fp.write('hello')
        fp.close()
        pmon = PathMonitor()
        pmon.add(self.path, function)
        pmon.check()
        self.assertFalse(function.called)
        sleep(0.01)
        fp = open(self.path, 'w')
        fp.write('world')
        fp.close()
        pmon.check()
        function.assert_called_with(self.path)
        function.reset_mock()
        pmon.check()
        self.assertFalse(function.called)

    def test_added(self):
        function = Mock()
        pmon = PathMonitor()
        pmon.add(self.path, function)
        pmon.check()
        self.assertFalse(function.called)
        fp = open(self.path, 'w+')
        fp.write('hello')
        fp.close()
        pmon.check()
        function.assert_called_with(self.path)
        function.reset_mock()
        pmon.check()
        self.assertFalse(function.called)