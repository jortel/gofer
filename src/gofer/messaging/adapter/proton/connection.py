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
from uuid import uuid4
from logging import getLogger

from proton import ConnectionException, LinkException
from proton import SSLDomain, SSLException
from proton.utils import BlockingConnection
from proton.reactors import DynamicNodeProperties

from gofer.common import ThreadSingleton
from gofer.messaging.adapter.reliability import YEAR
from gofer.messaging.adapter.model import Broker, BaseConnection, NotFound


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
    def ssl_domain(broker):
        """
        Get the ssl domain using the broker settings.
        :param broker: A broker.
        :type broker: gofer.messaging.adapter.model.Broker
        :return: The populated domain.
        :rtype: SSLDomain
        :raise: SSLException
        """
        domain = None
        if broker.use_ssl():
            domain = SSLDomain(SSLDomain.MODE_CLIENT)
            domain.set_trusted_ca_db(broker.ssl.ca_certificate)
            domain.set_credentials(
                broker.ssl.client_certificate,
                broker.ssl.client_key or broker.ssl.client_certificate, None)
            if broker.ssl.host_validation:
                mode = SSLDomain.VERIFY_PEER_NAME
            else:
                mode = SSLDomain.VERIFY_PEER
            domain.set_peer_authentication(mode)
        return domain

    def __init__(self, url):
        """
        :param url: The broker url.
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
        broker = Broker.find(self.url)
        url = broker.url.standard()
        while True:
            try:
                log.info('connecting: %s', broker)
                domain = self.ssl_domain(broker)
                self._impl = BlockingConnection(url, ssl_domain=domain)
                log.info('connected: %s', broker.url)
                break
            except (ConnectionException, SSLException):
                log.exception(url)
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
        :rtype: proton.utils.BlockingSender
        :raise: NotFound
        """
        try:
            name = str(uuid4())
            return self._impl.create_sender(address, name=name)
        except LinkException, le:
            raise NotFound(*le.args)

    def receiver(self, address=None, dynamic=False):
        """
        Get a message receiver for the specified address.
        :param address: An AMQP address.
        :type address: str
        :param dynamic: Indicates link address is dynamically assigned.
        :type dynamic: bool
        :return: A receiver.
        :rtype: proton.utils.BlockingReceiver
        :raise: NotFound
        """
        try:
            options = None
            name = str(uuid4())
            if dynamic:
                # needed by dispatch router
                options = DynamicNodeProperties({'x-opt-qd.address': unicode(address)})
                address = None
            return self._impl.create_receiver(address, name=name, dynamic=dynamic, options=options)
        except LinkException, le:
            raise NotFound(*le.args)

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
