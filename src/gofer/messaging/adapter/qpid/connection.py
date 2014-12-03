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

from qpid.messaging import Connection as RealConnection
from qpid.messaging.transports import TRANSPORTS

from gofer.messaging.adapter.model import Cloud, BaseConnection


log = getLogger(__name__)


class Connection(BaseConnection):
    """
    Represents a Qpid connection.
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

    def __init__(self, url):
        """
        :param url: The broker url.
        :type url: str
        """
        BaseConnection.__init__(self, url)
        self._impl = None

    def open(self):
        """
        Connect to the broker.
        :return: The AMQP connection object.
        :rtype: Connection
        """
        broker = Cloud.find(self.url)
        ssl = broker.ssl
        Connection.add_transports()
        log.info('connecting: %s', self)
        self._impl = RealConnection(
            host=broker.host,
            port=broker.port,
            tcp_nodelay=True,
            reconnect=True,
            transport=broker.scheme,
            username=broker.userid,
            password=broker.password,
            ssl_trustfile=ssl.ca_certificate,
            ssl_keyfile=ssl.client_key,
            ssl_certfile=ssl.client_certificate,
            ssl_skip_hostname_check=(not ssl.host_validation))
        self._impl.attach()
        log.info('connected: %s', self.url)
        return self

    def channel(self):
        return self._impl.session()

    def close(self):
        self._impl.close()
