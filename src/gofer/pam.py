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
    
    def __init__(self, userid, password):
        self.userid = userid
        self.password = password
    
    def __call__(self, auth, query_list):
        result = []
        for query, type_id in query_list:
            # prompt for a user
            if type_id == _PAM.PAM_PROMPT_ECHO_ON:
                result.append((self.userid, 0))
                continue
            # prompt for a password
            if type_id == _PAM.PAM_PROMPT_ECHO_OFF:
                result.append((self.password, 0))
                continue
        return result


class PAM(object):
    """
    PAM object used for authentication.
    :cvar SERVICE: The default service
    :type SERVICE: str
    """
    
    SERVICE = 'passwd'

    @staticmethod
    def authenticate(userid, password, service=None):
        """
        Authenticate the specified user.
        :param userid: A user name.
        :type userid: str
        :param password: A password.
        :type password: str
        :param service: The optional PAM service.
        :type service: str
        :raise Exception: when authentication fails.
        """
        if not service:
            service = PAM.SERVICE
        query = Query(userid, password)
        auth = _PAM.pam()
        auth.start(service, userid, query)
        auth.authenticate()
        auth.acct_mgmt()
