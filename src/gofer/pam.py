#
# Copyright (c) 2011 Red Hat, Inc.
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
# Requires: PyPAM
"""
PAM authentication classes.
"""

import PAM as _PAM
from logging import getLogger

log = getLogger(__name__)


class Query:
    
    def __init__(self, user, password):
        self.user = user
        self.password = password
    
    def __call__(self, auth, query_list):
        resp = []
        for query, type in query_list:
            # prompt for a user
            if type == _PAM.PAM_PROMPT_ECHO_ON:
                resp.append((self.user, 0))
                continue
            # prompt for a password
            if type == _PAM.PAM_PROMPT_ECHO_OFF:
                resp.append((self.password, 0))
                continue
        return resp


class PAM:
    """
    PAM object used for authentication.
    @cvar SERVICE: The default service
    @type SERVICE: str
    """
    
    SERVICE = 'passwd'

    def authenticate(self, user, password, service=None):
        """
        Authenticate the specified user.
        @param user: A user name.
        @type user: str
        @param password: A password.
        @type password: str
        @param service: The optional PAM service.
        @type service: str
        @raise Exception: when authentication fails.
        """
        if not service:
            service = self.SERVICE
        q = Query(user, password)
        auth = _PAM.pam()
        auth.start(service, user, q)
        auth.authenticate()
        auth.acct_mgmt()
