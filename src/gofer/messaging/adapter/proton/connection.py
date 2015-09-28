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

from time import sleep
from logging import getLogger

from proton import ConnectionException
from proton import SSLDomain, SSLException

from gofer.common import Thread, ThreadSingleton
from gofer.messaging.adapter.reliability import YEAR
from gofer.messaging.adapter.model import Connector, BaseConnection
from gofer.messaging.adapter.proton.reactor import Connection as RealConnection


log = getLogger(__name__)


DELAY = 10
MAX_DELAY = 90
RETRIES = YEAR / MAX_DELAY
DELAY_MULTIPLIER = 1.2


class Connection(BaseConnection):
    """
    Proton connection.
    """

    __metaclass__ = ThreadSingleton

    @staticmethod
    def ssl_domain(connector):
        """
        Get the ssl domain using the broker settings.
        :param connector: A broker.
        :type connector: Connector
        :return: The populated domain.
        :rtype: SSLDomain
        :raise: SSLException
        :raise: ValueError
        """
        domain = None
        if connector.use_ssl():
            connector.ssl.validate()
            domain = SSLDomain(SSLDomain.MODE_CLIENT)
            domain.set_trusted_ca_db(connector.ssl.ca_certificate)
            domain.set_credentials(
                connector.ssl.client_certificate,
                connector.ssl.client_key or connector.ssl.client_certificate, None)
            if connector.ssl.host_validation:
                mode = SSLDomain.VERIFY_PEER_NAME
            else:
                mode = SSLDomain.VERIFY_PEER
            domain.set_peer_authentication(mode)
        return domain

    def __init__(self, url):
        """
        :param url: The connector url.
        :type url: str
        """
        super(Connection, self).__init__(url)
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
        connector = Connector.find(self.url)
        url = connector.url.canonical
        while not Thread.aborted():
            try:
                log.info('connecting: %s', connector)
                ssl_domain = self.ssl_domain(connector)
                impl = RealConnection(url, heartbeat=10, ssl_domain=ssl_domain)
                self._impl = impl.open()
                log.info('connected: %s', connector.url)
                break
            except (ConnectionException, SSLException), e:
                log.error('connect: %s, failed: %s', self.url, e)
                if retries > 0:
                    log.info('retry in %d seconds', delay)
                    sleep(delay)
                    if delay < MAX_DELAY:
                        delay *= DELAY_MULTIPLIER
                    retries -= 1
                else:
                    raise

    def sender(self, address):
        """
        Get a message sender for the specified address.
        :param address: An AMQP address.
        :type address: str
        :return: A sender.
        :rtype: gofer.messaging.adapter.proton.reactor.Sender
        """
        return self._impl.sender(address)

    def receiver(self, address=None, dynamic=False):
        """
        Get a message receiver for the specified address.
        :param address: An AMQP address.
        :type address: str
        :param dynamic: Indicates link address is dynamically assigned.
        :type dynamic: bool
        :return: A receiver.
        :rtype: gofer.messaging.adapter.proton.reactor.Receiver
        """
        return self._impl.receiver(address, dynamic=dynamic)

    def close(self):
        """
        Close the connection.
        """
        connection = self._impl
        self._impl = None
        try:
            connection.close()
            connector = Connector.find(self.url)
            log.info('closed: %s', connector.url)
        except Exception:
            pass
