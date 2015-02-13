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

from gofer.common import ThreadSingleton
from gofer.messaging.adapter.reliability import YEAR
from gofer.messaging.adapter.model import Broker, BaseConnection


log = getLogger(__name__)

VIRTUAL_HOST = '/'
USERID = 'guest'
PASSWORD = 'guest'

CONNECTION_EXCEPTIONS = (IOError, SocketError, ConnectionError, AttributeError)

DELAY = 10
MAX_DELAY = 90
RETRIES = YEAR / MAX_DELAY
DELAY_MULTIPLIER = 1.2


class Connection(BaseConnection):
    """
    An AMQP broker connection.
    """

    __metaclass__ = ThreadSingleton

    @staticmethod
    def ssl_domain(broker):
        """
        Get SSL properties
        :param broker: A broker object.
        :type broker: gofer.messaging.adapter.model.Broker
        :return: The SSL properties
        :rtype: dict
        :raise: ValueError
        """
        domain = None
        if broker.use_ssl():
            domain = {}
            broker.ssl.validate()
            if broker.ssl.ca_certificate:
                required = ssl.CERT_REQUIRED
            else:
                required = ssl.CERT_NONE
            domain.update(
                cert_reqs=required,
                ca_certs=broker.ssl.ca_certificate,
                keyfile=broker.ssl.client_key,
                certfile=broker.ssl.client_certificate)
        return domain

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

    def open(self, retries=RETRIES, delay=DELAY):
        """
        Open a connection to the broker.
        :param retries: The number of retries.
        :type retries: int
        :param delay: The delay between retries in seconds.
        :type delay: int
        """
        if self.is_open():
            # already open
            return
        delay = float(delay)
        broker = Broker.find(self.url)
        host = ':'.join((broker.host, str(broker.port)))
        virtual_host = broker.virtual_host or VIRTUAL_HOST
        domain = self.ssl_domain(broker)
        userid = broker.userid or USERID
        password = broker.password or PASSWORD
        while True:
            try:
                log.info('connecting: %s', broker)
                self._impl = RealConnection(
                    host=host,
                    virtual_host=virtual_host,
                    ssl=domain,
                    userid=userid,
                    password=password,
                    confirm_publish=True)
                log.info('connected: %s', broker.url)
                break
            except CONNECTION_EXCEPTIONS:
                log.exception(str(self.url))
                if retries > 0:
                    log.info('retry in %d seconds', delay)
                    sleep(delay)
                    if delay < MAX_DELAY:
                        delay *= DELAY_MULTIPLIER
                    retries -= 1
                else:
                    raise

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
        except Exception:
            pass
