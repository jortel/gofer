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
Provides path and process monitoring classes.
"""

import os
from time import sleep
from threading import Thread, RLock
from logging import getLogger

log = getLogger(__name__)


class PathMonitor:
    """
    Path monitor.
    @ivar __paths: A list of paths to monitor.
    @type __paths: dict (path, cb)
    @ivar __mutex: The mutex.
    @type __mutex: RLock
    @ivar __thread: The optional thread.  see: start().
    @type __thread: Thread
    """

    def __init__(self):
        self.__paths = {}
        self.__mutex = RLock()
        self.__thread = None
        
    def add(self, path, cb):
        """
        Add a path to be monitored.
        @param path: An absolute path to monitor.
        @type path: str
        @param cb: A listener.
        @type cb: callable
        """
        self.__lock()
        try:
            self.__paths[path] = [0, cb]
        finally:
            self.__unlock()
        
    def delete(self, path):
        """
        Delete a path to be monitored.
        @param path: An absolute path to monitor.
        @type path: str
        """
        self.__lock()
        try:
            try:
                del self.__paths[path]
            except KeyError:
                pass
        finally:
            self.__unlock()
            
    def start(self, precision=1):
        """
        Start the monitor thread.
        @param precision: The precision (how often to check).
        @type precision: float
        @return: self
        @rtype: L{PathMonitor}
        """
        self.__lock()
        try:
            if self.__thread:
                raise Exception, 'already started'
            thread = MonitorThread(self, precision)
            thread.start()
            self.__thread = thread
            return self
        finally:
            self.__unlock()
    
    def join(self):
        """
        Join the monitoring thread.
        """
        if not self.__thread:
            raise Exception, 'not started'
        self.__thread.join()

    def check(self):
        """
        Check paths and notify.
        """
        self.__lock()
        try:
            paths = self.__paths.items()
        finally:
            self.__unlock()
        for k,v in paths:
            mtime = self.__mtime(k)
            if mtime != v[0]:
                self.__notify(k, v[1])
                v[0] = mtime
    
    def __notify(self, path, cb):
        try:
            cb(path)
        except:
            log.exception(path)                
    
    def __mtime(self, path):
        try:
            return os.path.getmtime(path)
        except OSError:
            return 0
        
    def __lock(self):
        self.__mutex.acquire()
        
    def __unlock(self):
        self.__mutex.release()


class MonitorThread(Thread):
    """
    Monitor thread.
    @ivar monitor: A monitor object.
    @type monitor: Monitor
    @ivar precision: The level of percision (seconds).
    @type precision: float
    """
    
    def __init__(self, monitor, precision):
        """
        @param monitor: A monitor object.
        @type monitor: Monitor
        @param precision: The level of percision (seconds).
        @type precision: float
        """
        Thread.__init__(self, name='PathMonitor%s' % precision)
        self.monitor = monitor
        self.precision = precision
        self.setDaemon(True)
        
    def run(self):
        """
        Thread main run().
        """
        monitor = self.monitor
        while True:
            monitor.check()
            sleep(self.precision)
