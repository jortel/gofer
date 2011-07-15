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
from time import sleep
from threading import RLock
from gofer.messaging import *
from gofer.messaging.broker import Broker
from gofer.messaging.transport import SSL
from qpid.messaging import Connection
from logging import getLogger

log = getLogger(__name__)


class SessionPool:
    """
    The AMQP session pool.
    """
    
    def __init__(self):
        self.__mutex = RLock()
        self.__pools = {}
        
    def get(self, url):
        """
        Get the next free session in the pool.
        @param url: A broker url.
        @type url: str
        @return: A free session.
        @rtype: qpid.messaging.Session
        """
        self.__lock()
        try:
            pool = self.__pool(url)
            ssn = self.__pop(pool)
            if ssn is None:
                broker = Broker(url)
                con = broker.connect()
                ssn = con.session()
            pool[1].append(ssn)
            return ssn
        finally:
            self.__unlock()
            
    def put(self, url, ssn):
        """
        Release a session back to the pool.
        @param url: A broker url.
        @type url: str
        @param ssn: An AMQP session.
        @rtype: qpid.messaging.Session
        """
        self.__lock()
        try:
            pool = self.__pool(url)
            if ssn in pool[1]:
                pool[1].remove(ssn)
            if ssn not in pool[0]:
                pool[0].append(ssn)
        finally:
            self.__unlock()
            
    def purge(self):
        """
        Purge (close) free sessions.
        """
        self.__lock()
        try:
            for pool in self.__pools.values():
                while pool[0]:
                    try:
                        ssn = pool.pop()
                        ssn.close()
                    except:
                        log.error(ssn, exc_info=1)
        finally:
            self.__unlock()
            
    def __pop(self, pool):
        """
        Pop the next available session from the free list.
        The session is acknowledge to purge it of stale transactions.
        @param pool: A pool (free,busy).
        @type pool: tuple
        @return: The popped session
        @rtype: qpid.messaging.Session
        """
        while pool[0]:
            ssn = pool[0].pop()
            try:
                ssn.acknowledge()
                return ssn
            except:
                log.error(ssn, exc_info=1)
        
    def __pool(self, url):
        """
        Obtain the pool for the specified url.
        @param url: A broker url.
        @type url: str
        @return: The session pool.  (free,busy)
        @rtype: tuple
        """
        self.__lock()
        try:
            pool = self.__pools.get(url)
            if pool is None:
                pool = ([],[])
                self.__pools[url] = pool
            return pool
        finally:
            self.__unlock()
        
    def __lock(self):
        self.__mutex.acquire()
        
    def __unlock(self):
        self.__mutex.release()


class Endpoint:
    """
    Base class for QPID endpoint.
    @cvar ssnpool: An AMQP session pool.
    @type ssnpool: L{SessionPool}
    @ivar uuid: The unique endpoint id.
    @type uuid: str
    @ivar url: The broker URL.
    @type url: str
    @ivar __mutex: The endpoint mutex.
    @type __mutex: RLock
    @ivar __session: An AMQP session.
    @type __session: qpid.messaging.Session
    """

    LOCALHOST = 'tcp://localhost:5672'
    
    ssnpool = SessionPool()

    def __init__(self, uuid=getuuid(), url=LOCALHOST):
        """
        @param uuid: The endpoint uuid.
        @type uuid: str
        @param url: The broker url <transport>://<user>/<pass>@<host>:<port>.
        @type url: str
        """
        self.uuid = uuid
        self.url = url
        self.__mutex = RLock()
        self.__session = None
        atexit.register(self.close)

    def id(self):
        """
        Get the endpoint id
        @return: The id.
        @rtype: str
        """
        return self.uuid

    def session(self):
        """
        Get a session for the open connection.
        @return: An open session.
        @rtype: qpid.messaging.Session
        """
        self._lock()
        try:
            if self.__session is None:
                self.__session = self.ssnpool.get(self.url)
                log.debug('{%s} connected to AMQP' % self.id())
            return self.__session
        finally:
            self._unlock()

    def ack(self):
        """
        Acknowledge all messages received on the session.
        """
        try:
            self.__session.acknowledge()
        except:
            pass

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
            self.ssnpool.put(self.url, self.__session)
            self.__session = None
        finally:
            self._unlock()
            
    def _lock(self):
        self.__mutex.acquire()
        
    def _unlock(self):
        self.__mutex.release()

    def __parsedurl(self):
        urlpart = self.url.split('://', 1)
        if len(urlpart) == 1:
            return (urlpart[0], 'tcp')
        else:
            return (urlpart[0], urlpart[1])

    def __del__(self):
        try:
            self.close()
        except:
            log.error(self.uuid, exc_info=1)

    def __str__(self):
        return 'Endpoint id:%s broker @ %s' % (self.id(), self.url)
