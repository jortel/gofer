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

from time import sleep
from logging import getLogger
from socket import error as SocketError

from amqp import Connection as RealConnection
from amqp import ConnectionError

from gofer.messaging.adapter.model import Cloud, BaseConnection


log = getLogger(__name__)

VIRTUAL_HOST = '/'
USERID = 'guest'
PASSWORD = 'guest'

CONNECTION_EXCEPTIONS = (IOError, SocketError, ConnectionError, AttributeError)


class Connection(BaseConnection):
    """
    A generic AMQP broker connection.
    """

    @staticmethod
    def _ssl(broker):
        """
        Get SSL properties
        :param broker: A broker object.
        :type broker: gofer.messaging.Broker
        :return: The SSL properties
        :rtype: dict
        """
        if not broker.url.is_ssl():
            return
        if broker.ssl.ca_certificate:
            required = ssl.CERT_REQUIRED
        else:
            required = ssl.CERT_NONE
        return dict(
            cert_reqs=required,
            ca_certs=broker.ssl.ca_certificate,
            keyfile=broker.ssl.client_keykey,
            certfile=broker.ssl.client_certificate)

    def __init__(self, url):
        """
        :param url: The broker url.
        :type url: str
        """
        BaseConnection.__init__(self, url)
        self._impl = None

    def open(self, retries=10000, delay=4):
        """
        Open a connection to the broker.
        :param retries: The number of retries.
        :type retries: int
        :param delay: The delay between retries in seconds.
        :type delay: int
        :return:
        """
        while True:
            try:
                log.info('connecting: %s', self)
                broker = Cloud.find(self.url)
                self._impl = RealConnection(
                    host=':'.join((broker.host, str(broker.port))),
                    virtual_host=broker.virtual_host or VIRTUAL_HOST,
                    ssl=self._ssl(broker),
                    userid=broker.userid or USERID,
                    password=broker.password or PASSWORD)
                log.info('connected: %s', self.url)
                return self
            except CONNECTION_EXCEPTIONS:
                log.exception(str(self.url))
                if retries > 0:
                    sleep(delay)
                    retries -= 1
                else:
                    raise

    def channel(self):
        return self._impl.channel()

    def close(self):
        """
        Close the connection to the broker.
        """
        try:
            self._impl.close()
        except CONNECTION_EXCEPTIONS:
            # ignored
            pass
