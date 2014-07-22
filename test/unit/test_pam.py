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

from mock import patch

from gofer import pam


class Test(TestCase):

    @patch('gofer.pam.pam_end')
    @patch('gofer.pam.pam_authenticate')
    @patch('gofer.pam.pam_start')
    def test_authenticated(self, _start, _authenticate, _end):
        _start.return_value = 0
        _authenticate.return_value = 0
        user = 'user'
        password = 'password'
        service = 'login'
        valid = pam.authenticate(user, password, service)
        self.assertTrue(_start.called)
        self.assertTrue(_authenticate.called)
        self.assertTrue(_end.called)
        self.assertTrue(valid)

    @patch('gofer.pam.pam_end')
    @patch('gofer.pam.pam_authenticate')
    @patch('gofer.pam.pam_start')
    def test_start_failed(self, _start, _authenticate, _end):
        _start.return_value = -1
        _authenticate.return_value = 0
        user = 'user'
        password = 'password'
        service = 'login'
        valid = pam.authenticate(user, password, service)
        self.assertTrue(_start.called)
        self.assertFalse(_authenticate.called)
        self.assertFalse(_end.called)
        self.assertFalse(valid)

    @patch('gofer.pam.pam_end')
    @patch('gofer.pam.pam_authenticate')
    @patch('gofer.pam.pam_start')
    def test_not_authenticated(self, _start, _authenticate, _end):
        _start.return_value = 0
        _authenticate.return_value = 1
        user = 'user'
        password = 'password'
        service = 'login'
        valid = pam.authenticate(user, password, service)
        self.assertTrue(_start.called)
        self.assertTrue(_authenticate.called)
        self.assertTrue(_end.called)
        self.assertFalse(valid)

    @patch('gofer.pam.pam_end')
    @patch('gofer.pam.pam_authenticate')
    @patch('gofer.pam.pam_start')
    def test_exception_raised(self, _start, _authenticate, _end):
        _start.return_value = 0
        _authenticate.side_effect = ValueError
        user = 'user'
        password = 'password'
        service = 'login'
        valid = pam.authenticate(user, password, service)
        self.assertTrue(_start.called)
        self.assertTrue(_authenticate.called)
        self.assertFalse(_end.called)
        self.assertFalse(valid)
