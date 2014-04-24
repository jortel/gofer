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

import PAM as _PAM
from unittest import TestCase

from mock import patch

from gofer.pam import Query, PAM


USERID = 'test-user'
PASSWORD = 'test-password'


class TestQuery(TestCase):

    def test_init(self):
        query = Query(USERID, PASSWORD)
        self.assertEqual(query.user, USERID)
        self.assertEqual(query.password, PASSWORD)

    def test_call(self):
        query_list = [
            (None, _PAM.PAM_PROMPT_ECHO_ON),
            (None, _PAM.PAM_PROMPT_ECHO_OFF)
        ]
        query = Query(USERID, PASSWORD)
        result = query(None, query_list)
        self.assertEqual(result[0], (USERID, 0))
        self.assertEqual(result[1], (PASSWORD, 0))


class TestPAM(TestCase):

    def test_init(self):
        self.assertEqual(PAM.SERVICE, 'passwd')

    @patch('gofer.pam.Query')
    @patch('gofer.pam._PAM.pam')
    def test_authenticate(self, _pam, _query):
        pam = PAM()
        # default service
        pam.authenticate(USERID, PASSWORD)
        _pam().start.assert_called_with(PAM.SERVICE, USERID, _query())
        _pam().authenticate.assert_called_with()
        # specified service
        pam.authenticate(USERID, PASSWORD, service='ssh')
        _pam().start.assert_called_with('ssh', USERID, _query())
        _pam().authenticate.assert_called_with()
