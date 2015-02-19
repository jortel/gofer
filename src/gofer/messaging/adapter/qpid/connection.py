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

from time import sleep
from logging import getLogger

from qpid.messaging import Connection as RealConnection
from qpid.messaging.transports import TRANSPORTS
from qpid.messaging import ConnectionError

from gofer.common import Thread, ThreadSingleton
from gofer.messaging.adapter.reliability import YEAR
from gofer.messaging.adapter.model import Connector, BaseConnection


log = getLogger(__name__)

# qpid transports
AMQP = 'amqp'
AMQPS = 'amqps'
TCP = 'tcp'
SSL = 'ssl'

DELAY = 10
MAX_DELAY = 90
RETRIES = YEAR / MAX_DELAY
DELAY_MULTIPLIER = 1.2


class Connection(BaseConnection):
    """
    Represents a Qpid connection.
    """

    __metaclass__ = ThreadSingleton

    @staticmethod
    def add_transports():
        """
        Ensure that well-known AMQP services are mapped.
        """
        key = AMQP
        if key not in TRANSPORTS:
            TRANSPORTS[key] = TRANSPORTS[TCP]
        key = AMQPS
        if key not in TRANSPORTS:
            TRANSPORTS[key] = TRANSPORTS[SSL]

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
        domain = {}
        if connector.use_ssl():
            connector.ssl.validate()
            domain.update(
                ssl_trustfile=connector.ssl.ca_certificate,
                ssl_keyfile=connector.ssl.client_key,
                ssl_certfile=connector.ssl.client_certificate,
                ssl_skip_hostname_check=(not connector.ssl.host_validation))
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
        connector = Connector.find(self.url)
        Connection.add_transports()
        domain = self.ssl_domain(connector)
        log.info('connecting: %s', connector)
        while not Thread.aborted():
            try:
                impl = RealConnection(
                    host=connector.host,
                    port=connector.port,
                    tcp_nodelay=True,
                    transport=connector.url.scheme,
                    username=connector.userid,
                    password=connector.password,
                    heartbeat=10,
                    **domain)
                impl.attach()
                self._impl = impl
                log.info('connected: %s', connector.url)
                break
            except ConnectionError, e:
                log.error('connect: %s, failed: %s', str(self.url), e)
                if retries > 0:
                    log.info('retry in %d seconds', delay)
                    sleep(delay)
                    if delay < MAX_DELAY:
                        delay *= DELAY_MULTIPLIER
                    retries -= 1
                else:
                    raise

    def session(self):
        """
        Open a session.
        :return The *real* channel.
        :rtype qpid.session.Session
        """
        return self._impl.session()

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
