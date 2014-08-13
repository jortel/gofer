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
from logging import getLogger

from mock import patch

from gofer.agent.logutil import LogHandler

log = getLogger(__file__)


class Test(TestCase):

    def setUp(self):
        LogHandler.install()

    def tearDown(self):
        LogHandler.uninstall()

    @patch('gofer.agent.logutil.SysLogHandler.emit')
    def test_handler(self, _emit):
        msg = 'This is a test.'

        # test
        log.info(msg)

        # validation
        calls = _emit.call_args_list
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0][1].msg, msg)

    @patch('gofer.agent.logutil.SysLogHandler.emit')
    def test_exception(self, _emit):
        msg = 'This is a test.'
        log.info(msg)

        # test
        try:
            raise ValueError('Testing')
        except ValueError:
            log.exception(msg)

        # validation
        self.assertEqual(_emit.call_count, 6)