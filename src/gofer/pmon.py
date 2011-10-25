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
from gofer import Singleton
from threading import Thread, RLock
from logging import getLogger

log = getLogger(__name__)


class PathMonitor(Thread):
    """
    Path monitor.
    """
    
    __metaclass__ = Singleton

    def __init__(self, precision=1):
        """
        @param precision: The precision (how often to check).
        @type precision: float
        """
        Thread.__init__(self, name='PathMonitor%s' % precision)
        self.__precision = precision
        self.__paths = {}
        self.__mutex = RLock()
        self.setDaemon(True)
        self.start()
        
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

    def run(self):
        """
        Thread main run().
        """
        while True:
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
            sleep(self.__precision)
    
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

def cb(path): print '%s, changed' % path

pm = PathMonitor()
pm.add('/tmp/cert', cb)
pm.join()