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
import errno
from hashlib import sha256
from time import sleep
from threading import Thread, RLock
from logging import getLogger

log = getLogger(__name__)


class PathMonitor:
    """
    Path monitor.
    @ivar __paths: A list of paths to monitor.
    @type __paths: dict path:(mtime, digest, cb)
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
            self.__paths[path] = [0, None, cb]
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
            self.__sniff(k, v)
            
    def __sniff(self, path, stat):
        """
        Sniff and compare the stats of the file at the
        specified I{path}.
        First, check the modification time, if different, then
        check the I{hash} of the file content to see if it really
        changed.  If changed, notify the registered listener.
        @param path: The path of the file to sniff.
        @type path: str
        @param stat: The cached stat (mtime, digest, cb)
        @type stat: tuple
        """
        try:
            f = File(path)
            mtime = f.mtime()
            if mtime == stat[0]:
                return
            digest = f.digest()
            if (digest and stat[1]) and (digest == stat[1]):
                return
            self.__notify(path, stat[2])
            stat[0] = mtime
            stat[1] = digest
        except:
            log.exception(path)
    
    def __notify(self, path, cb):
        """
        Safely invoke registered callback.
        @param path: The path of the changed file.
        @type path: str
        @param cb: A registered callback.
        @type cb: callable
        """
        try:
            cb(path)
        except:
            log.exception(path)

    def __lock(self):
        self.__mutex.acquire()
        
    def __unlock(self):
        self.__mutex.release()
        

class File:
    """
    Safe file operations.
    @ivar path: The path.
    @type path: str
    @ivar fp: The python file object.
    @type fp: fileobj
    """
    
    def __init__(self, path):
        """
        @param path: The file path.
        @type path: str        
        """
        self.path = path
        self.fp = None
        
    def open(self):
        """
        Open (if not already open)
        """
        if not self.fp:
            self.fp = open(self.path)
    
    def close(self):
        """
        Close (if not already closed)
        """
        if self.fp:
            self.fp.close()
            self.fp = None
            
    def read(self, n):
        """
        Read (n) bytes.
        @param n: The bytes to read.
        @type n: int
        @return: the bytes read.
        @rtype: buffer
        """
        return self.fp.read(n)
    
    def mtime(self):
        """
        Get modification time.
        @return: mtime
        @rtype: int
        """
        try:
            return os.path.getmtime(self.path)
        except OSError:
            pass
        except:
            log.exception(self.path)
        return 0 
    
    def digest(self):
        """
        Get the SHA256 hex digest for content.
        @return: the hexdigest.
        @rtype: str
        """
        try:
            self.open()
            h = sha256()
            while True:
                s = self.read(10240)
                if s:
                    h.update(s)
                else:
                    break
            self.close()
            return h.hexdigest()
        except IOError:
            pass
        except:
            log.exception(self.path)
        return None
        
    def __del__(self):
        self.close()


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




if __name__ == '__main__':
    def changed(path):
        print 'changed: %s' % path
    from logging import basicConfig
    basicConfig()
    pmon = PathMonitor()
    pmon.add('/tmp/jeff.repo', changed)
    pmon.start()
    pmon.join()