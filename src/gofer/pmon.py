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

from hashlib import sha256
from time import sleep
from threading import Thread, RLock
from logging import getLogger

log = getLogger(__name__)


# --- utils ------------------------------------------------------------------

def last_modified(path):
    """
    Get modification time.
    :param path: The absolute path to a file.
    :type path: str
    :return: The file modification time.
    :rtype: int
    """
    try:
        return os.path.getmtime(path)
    except OSError:
        pass
    except:
        log.exception(path)
    return 0


def digest(path):
    """
    Get the SHA256 hex digest for content.
    :param path: The absolute path to a file.
    :type path: str
    :return: the digest.
    :rtype: str
    """
    try:
        h = sha256()
        fp = open(path)
        try:
            while True:
                s = fp.read(10240)
                if s:
                    h.update(s)
                else:
                    break
            return h.hexdigest()
        finally:
            fp.close()
    except IOError:
        pass
    except:
        log.exception(path)
    return None


# --- monitor ----------------------------------------------------------------


class PathMonitor:
    """
    Path monitor.
    :ivar __paths: A list of paths to monitor.
    :type __paths: list path:[last_modified, digest, function]
    :ivar __mutex: The mutex.
    :type __mutex: RLock
    :ivar __thread: The optional thread.  see: start().
    :type __thread: Thread
    """

    def __init__(self):
        self.__paths = {}
        self.__mutex = RLock()
        self.__thread = None
        
    def add(self, path, target):
        """
        Add a path to be monitored.
        :param path: An absolute path to monitor.
        :type path: str
        :param target: Called when a change at path is detected.
        :type target: callable
        """
        self.__lock()
        try:
            self.__paths[path] = [last_modified(path), digest(path), target]
        finally:
            self.__unlock()
        
    def delete(self, path):
        """
        Delete a path to be monitored.
        :param path: An absolute path to monitor.
        :type path: str
        """
        self.__lock()
        try:
            try:
                del self.__paths[path]
            except KeyError:
                pass
        finally:
            self.__unlock()
            
    def start(self, precision=1.0):
        """
        Start the monitor thread.
        :param precision: The precision (how often to check).
        :type precision: float
        :return: self
        :rtype: PathMonitor
        """
        self.__lock()
        try:
            if self.__thread:
                raise Exception('already started')
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
            raise Exception('not started')
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
        for k, v in paths:
            self.__sniff(k, v)
            
    def __sniff(self, path, stat):
        """
        Sniff and compare the stats of the file at the specified *path*.
        First, check the modification time, if different, then
        check the *hash* of the file content to see if it really
        changed.  If changed, notify the registered listener.
        :param path: The path of the file to sniff.
        :type path: str
        :param stat: The cached stat [last_modified, digest, target]
        :type stat: list
        """
        try:
            current = [0, None]
            current[0] = last_modified(path)
            if current[0] == stat[0]:
                return
            current[1] = digest(path)
            if (current[1] and stat[1]) and (current[1] == stat[1]):
                return
            self.__notify(path, stat[2])
            stat[0] = current[0]
            stat[1] = current[1]
        except:
            log.exception(path)
    
    def __notify(self, path, target):
        """
        Safely invoke registered callback.
        :param path: The path of the changed file.
        :type path: str
        :param target: A registered callback.
        :type target: callable
        """
        try:
            target(path)
        except:
            log.exception(path)

    def __lock(self):
        self.__mutex.acquire()
        
    def __unlock(self):
        self.__mutex.release()
        

class MonitorThread(Thread):
    """
    Monitor thread.
    :ivar monitor: A monitor object.
    :type monitor: PathMonitor
    :ivar precision: The level of precision (seconds).
    :type precision: float
    """
    
    def __init__(self, monitor, precision):
        """
        :param monitor: A monitor object.
        :type monitor: PathMonitor
        :param precision: The level of precision (seconds).
        :type precision: float
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
