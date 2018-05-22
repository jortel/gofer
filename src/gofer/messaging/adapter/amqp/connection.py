# Copyright (c) 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import ssl

from logging import getLogger
from six import with_metaclass
from socket import error as SocketError

from amqp import Connection as RealConnection
from amqp import ConnectionError

from gofer.compat import str
from gofer.common import ThreadSingleton
from gofer.messaging.adapter.model import Connector, BaseConnection
from gofer.messaging.adapter.connect import retry


log = getLogger(__name__)

VIRTUAL_HOST = '/'
USERID = 'guest'
PASSWORD = 'guest'

CONNECTION_EXCEPTIONS = (IOError, SocketError, ConnectionError, AttributeError)


class Connection(with_metaclass(ThreadSingleton, BaseConnection)):
    """
    An AMQP broker connection.
    """

    @staticmethod
    def ssl_domain(connector):
        """
        Get SSL properties
        :param connector: A broker object.
        :type connector: Connector
        :return: The SSL properties
        :rtype: dict
        :raise: ValueError
        """
        domain = None
        if connector.use_ssl():
            domain = {}
            connector.ssl.validate()
            if connector.ssl.ca_certificate:
                required = ssl.CERT_REQUIRED
            else:
                required = ssl.CERT_NONE
            domain.update(
                cert_reqs=required,
                ca_certs=connector.ssl.ca_certificate,
                keyfile=connector.ssl.client_key,
                certfile=connector.ssl.client_certificate)
        return domain

    def __init__(self, url):
        """
        :param url: The connector url.
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

    @retry(*CONNECTION_EXCEPTIONS)
    def open(self):
        """
        Open a connection to the broker.
        """
        if self.is_open():
            # already open
            return
        connector = Connector.find(self.url)
        host = ':'.join((connector.host, str(connector.port)))
        virtual_host = connector.virtual_host or VIRTUAL_HOST
        domain = self.ssl_domain(connector)
        userid = connector.userid or USERID
        password = connector.password or PASSWORD
        log.info('open: %s', connector)
        self._impl = RealConnection(
            host=host,
            virtual_host=virtual_host,
            ssl=domain,
            userid=userid,
            password=password,
            confirm_publish=True)
        self._impl.connect()
        log.info('opened: %s', self.url)

    def channel(self):
        """
        Open a channel.
        :return The *real* channel.
        """
        return self._impl.channel()

    def close(self):
        """
        Close the connection.
        """
        connection = self._impl
        self._impl = None
        try:
            connection.close()
            log.info('closed: %s', self.url)
        except Exception as pe:
            log.exception(str(pe))
