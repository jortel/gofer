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
AMQP endpoint base classes.
"""

import atexit

from threading import RLock
from logging import getLogger

from qpid.messaging import Disposition, RELEASED, REJECTED

from gofer.messaging.adapter.model import BaseEndpoint
from gofer.messaging.adapter.qpid.broker import Broker


log = getLogger(__name__)


class Endpoint(BaseEndpoint):
    """
    Base class for an AMQP endpoint.
    :ivar __mutex: The endpoint mutex.
    :type __mutex: RLock
    :ivar __session: An AMQP session.
    :type __session: qpid.messaging.Session
    """

    def __init__(self, url):
        """
        :param url: The broker url <adapter>://<user>/<pass>@<host>:<port>.
        :type url: str
        """
        BaseEndpoint.__init__(self, url)
        self.__mutex = RLock()
        self.__session = None
        atexit.register(self.close)

    def channel(self):
        """
        Get a session for the open connection.
        :return: An open session.
        :rtype: qpid.messaging.Session
        """
        self._lock()
        try:
            if self.__session is None:
                broker = Broker(self.url)
                connection = broker.connect()
                self.__session = connection.session()
            return self.__session
        finally:
            self._unlock()

    def ack(self, message):
        """
        Acknowledge all messages received on the session.
        :param message: The message to acknowledge.
        :type message: qpid.messaging.Message
        """
        self.__session.acknowledge(message=message)

    def reject(self, message, requeue=True):
        """
        Reject the specified message.
        :param message: The message to reject.
        :type message: qpid.messaging.Message
        :param requeue: Requeue the message or discard it.
        :type requeue: bool
        """
        if requeue:
            disposition = Disposition(RELEASED)
        else:
            disposition = Disposition(REJECTED)
        self.__session.acknowledge(message=message, disposition=disposition)

    def open(self):
        """
        Open and configure the endpoint.
        """
        pass

    def close(self):
        """
        Close (shutdown) the endpoint.
        """
        self._lock()
        try:
            if self.__session is None:
                return
            self.__session.close()
            self.__session = None
        finally:
            self._unlock()
            
    def _lock(self):
        self.__mutex.acquire()
        
    def _unlock(self):
        self.__mutex.release()

    def __del__(self):
        try:
            self.close()
        except:
            log.error(self.uuid, exc_info=1)

    def __str__(self):
        return 'Endpoint id:%s broker @ %s' % (self.id(), self.url)

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *unused):
        self.close()
