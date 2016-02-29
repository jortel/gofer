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

    @patch('gofer.pam.Lib')
    def test_authenticated(self, lib):
        lib.pam_start.return_value = 0
        lib.pam_authenticate.return_value = 0
        user = 'user'
        password = 'password'
        service = 'login'
        valid = pam.authenticate(user, password, service)
        self.assertTrue(lib.pam_start.called)
        self.assertTrue(lib.pam_authenticate.called)
        self.assertTrue(lib.pam_end.called)
        self.assertTrue(lib.load.called)
        self.assertTrue(valid)

    @patch('gofer.pam.Lib')
    def test_start_failed(self, lib):
        lib.pam_start.return_value = -1
        lib.pam_authenticate.return_value = 0
        user = 'user'
        password = 'password'
        service = 'login'
        valid = pam.authenticate(user, password, service)
        self.assertTrue(lib.load.called)
        self.assertTrue(lib.pam_start.called)
        self.assertFalse(lib.pam_authenticate.called)
        self.assertFalse(lib.pam_end.called)
        self.assertFalse(valid)

    @patch('gofer.pam.Lib')
    def test_not_authenticated(self, lib):
        lib.pam_start.return_value = 0
        lib.pam_authenticate.return_value = 1
        user = 'user'
        password = 'password'
        service = 'login'
        valid = pam.authenticate(user, password, service)
        self.assertTrue(lib.load.called)
        self.assertTrue(lib.pam_start.called)
        self.assertTrue(lib.pam_authenticate.called)
        self.assertTrue(lib.pam_end.called)
        self.assertFalse(valid)

    @patch('gofer.pam.Lib')
    def test_exception_raised(self, lib):
        lib.pam_start.return_value = 0
        lib.pam_authenticate.side_effect = ValueError
        user = 'user'
        password = 'password'
        service = 'login'
        valid = pam.authenticate(user, password, service)
        self.assertTrue(lib.load.called)
        self.assertTrue(lib.pam_start.called)
        self.assertTrue(lib.pam_authenticate.called)
        self.assertFalse(lib.pam_end.called)
        self.assertFalse(valid)
