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

"""
Contains custom QPID transport classes.
"""

import ssl
from gofer.messaging.broker import Broker
from qpid.messaging.transports import connect, TRANSPORTS, tls
from logging import getLogger

log = getLogger(__name__)


class SSL(tls):
    """
    SSL Transport.
    Extends L{tls} to support client certificates.
    """

    def __init__(self, *args):
        """
        @param args: The argument list.
        Using arglist for compatability with many versions
        For <= 0.8  passed (host, port)
        For 0.10 (el6) passed (con, host, port)
        @type args: list
        """
        host, port = args[-2:]
        url = ':'.join((host,str(port)))
        broker = Broker(url)
        if broker.cacert:
            reqcert = ssl.CERT_REQUIRED
        else:
            reqcert = ssl.CERT_NONE
        self.socket = connect(host, port)
        self.tls = \
            ssl.wrap_socket(
                self.socket,
                cert_reqs=reqcert,
                ca_certs=broker.cacert,
                certfile=broker.clientcert)
        self.socket.setblocking(0)
        self.state = None
        
#
# Install the transport.
#
TRANSPORTS['ssl'] = SSL
