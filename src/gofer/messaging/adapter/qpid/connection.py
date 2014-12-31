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

from gofer.messaging.adapter.model import Domain, BaseConnection, SharedConnection


log = getLogger(__name__)


class Connection(BaseConnection):
    """
    Represents a Qpid connection.
    """

    __metaclass__ = SharedConnection

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

    def is_open(self):
        """
        Get whether the connection has been opened.
        :return: True if open.
        :rtype bool
        """
        return self._impl is not None

    def open(self):
        """
        Open the connection.
        """
        if self.is_open():
            # already open
            return
        broker = Domain.broker.find(self.url)
        ssl = broker.ssl
        Connection.add_transports()
        log.info('connecting: %s', broker)
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
        log.info('connected: %s', broker.url)

    @property
    def impl(self):
        """
        Get the *real* connection.
        :return: The real connection.
        :rtype: qpid.messaging.Connection
        """
        return self._impl

    def channel(self):
        """
        Open a channel.
        :return The *real* channel.
        :rtype qpid.session.Session
        """
        return self._impl.session()

    def close(self, hard=False):
        """
        Close the connection.
        A *soft* close is essentially a non-operation and provides
        for connection caching.  A *hard* close actually closes the
        connection to the broker.
        :param hard: Force the connection closed.
        :type hard: bool
        """
        if not self.is_open():
            # not open
            return
        if not hard:
            # soft
            return
        self._disconnect()
        self._impl = None

    def _disconnect(self):
        """
        Safely close the *real* connection.
        """
        try:
            self._impl.close()
        except Exception, e:
            log.debug(str(e))
