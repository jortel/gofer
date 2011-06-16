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


class SSLTransport(tls):
    """
    SSL Transport.
    """

    def __init__(self, broker):
        """
        @param broker: An amqp broker.
        @type broker: L{Broker}
        """
        url = broker.url
        self.socket = connect(url.host, url.port)
        if broker.cacert:
            reqcert = ssl.CERT_REQUIRED
        else:
            reqcert = ssl.CERT_NONE
        self.tls = ssl.wrap_socket(
                self.socket,
                cert_reqs=reqcert,
                ca_certs = broker.cacert,
                certfile = broker.clientcert)
        self.socket.setblocking(0)
        self.state = None


class SSLFactory:
    """
    Factory used to create a transport.
    """

    def __call__(self, host, port):
        """
        @param host: A host or IP.
        @type host: str
        @param port: A tcp port.
        @type port: int
        """
        url = '%s:%d' % (host, port)
        broker = Broker(url)
        transport = SSLTransport(broker)
        return transport

#
# Install the transport.
#
TRANSPORTS['ssl'] = SSLFactory()
