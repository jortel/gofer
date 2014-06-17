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
Defined Qpid broker objects.
"""

from logging import getLogger

from qpid.messaging import Connection
from qpid.messaging.transports import TRANSPORTS

from gofer.transport.broker import Broker


log = getLogger(__name__)


DEFAULT_URL = 'amqp://localhost'


class Qpid(Broker):
    """
    Represents a Qpid broker.
    """

    @staticmethod
    def add_transports():
        """
        Ensure that well-known AMQP services are mapped.
        """
        key = 'amqp'
        if key not in TRANSPORTS:
            TRANSPORTS[key] = TRANSPORTS['tcp']
        key = 'amqps'
        if key not in TRANSPORTS:
            TRANSPORTS[key] = TRANSPORTS['ssl']

    def __init__(self, url=None):
        """
        :param url: The broker url <transport>://<host>:<port>.
        :type url: str
        """
        Broker.__init__(self, url or DEFAULT_URL)

    def connect(self):
        """
        Connect to the broker.
        :return: The AMQP connection object.
        :rtype: Qpid
        """
        Qpid.add_transports()
        try:
            return self.connection.cached
        except AttributeError:
            url = self.url.simple()
            log.info('connecting: %s', self)
            con = Connection(
                host=self.host,
                port=self.port,
                tcp_nodelay=True,
                reconnect=True,
                transport=self.transport,
                username=self.userid,
                password=self.password,
                ssl_trustfile=self.cacert,
                ssl_certfile=self.clientcert,
                ssl_skip_hostname_check=(not self.host_validation))
            con.attach()
            self.connection.cached = con
            log.info('{%s} connected to AMQP', self.id())
            return con

    def close(self):
        """
        Close the connection to the broker.
        """
        try:
            self.connection.cached.close()
            del self.connection.cached
        except AttributeError:
            pass
