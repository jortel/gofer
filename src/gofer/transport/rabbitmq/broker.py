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

from librabbitmq import Connection, ConnectionError

from gofer.transport.broker import Broker


log = getLogger(__name__)


VIRTUAL_HOST = '/'
USERID = 'guest'
PASSWORD = 'guest'
DEFAULT_URL = 'amqp://localhost'


class RabbitMQ(Broker):
    """
    A RabbitMQ broker.
    """

    def __init__(self, url=DEFAULT_URL):
        """
        :param url: The broker url <transport>://<host>:<port>.
        :type url: str
        """
        Broker.__init__(self, url)

    def connect(self):
        """
        Establish a connection to the broker.
        :return: The open connection.
        :rtype: Connection
        """
        try:
            return self.connection.cached
        except AttributeError:
            con = self.open()
            self.connection.cached = con
            log.info('{%s} connected to AMQP', self.id())
            return con

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
                log.info('connecting:\n%s', self)
                con = Connection(
                    host=self.url.host,
                    virtual_host=self.virtual_host or VIRTUAL_HOST,
                    port=self.url.port,
                    userid=self.userid or USERID,
                    password=self.password or PASSWORD)
                return con
            except ConnectionError:
                log.exception(str(self.url))
                if retries > 0:
                    sleep(delay)
                    retries -= 1
                else:
                    raise

    def close(self):
        """
        Close the connection to the broker.
        """
        try:
            con = self.connection.cached
            del self.connection.cached
            con.close()
        except AttributeError:
            # not open
            pass
        except ConnectionError:
            # ignored
            pass
