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
Contains locking classes.
"""

import os
import fcntl

from threading import RLock

from gofer.compat import str
from gofer.common import mkdir


class LockFailed(Exception):
    pass


class NotLocked(Exception):
    pass


class LockFile:
    """
    File based locking.
    :ivar path: The absolute path to the lock file.
    :type path: str
    :ivar __fp: The *file pointer* to the lock file.
    :type __fp: *file-like* pointer.
    """

    def __init__(self, path):
        """
        :param path: The absolute path to the lock file.
        :type path: str
        """
        self.path = path
        self.__fp = None
        mkdir(os.path.dirname(path))

    def acquire(self, blocking=True):
        """
        Acquire the lockfile.
        :param blocking: Wait for the lock.
        :type blocking: bool
        :return: self
        :rtype: LockFile
        """ 
        fp = open(self.path, 'w')
        if not blocking:
            try:
                fcntl.flock(fp.fileno(), fcntl.LOCK_EX|fcntl.LOCK_NB)
            except IOError:
                fp.close()
                raise LockFailed(self.path)
        else:
            fcntl.flock(fp.fileno(), fcntl.LOCK_EX)
        self.__fp = fp
        self.setpid()
        return self

    def release(self):
        """
        Release the lockfile.
        """
        try:
            if not self.__fp.closed:
                self.__fp.close()
        except Exception:
            pass
    
    def getpid(self):
        """
        Get the process id.
        :return: The pid in the lock file, else the current pid.
        :rtype: int
        """
        pid = 0
        with open(self.path) as fp:
            content = fp.read()
        if content:
            pid = int(content)
        return pid

    def setpid(self, pid=os.getpid()):
        """
        Write our procecss id and flush.
        :param pid: The process ID.
        :type pid: int
        """
        self.__fp.seek(0)
        self.__fp.write(str(pid))
        self.__fp.flush()
        

class Lock:
    """
    File backed Reentrant lock.
    """

    def __init__(self, path):
        self.__depth = 0
        self.__mutex = RLock()
        self.__lockf = LockFile(path)

    def acquire(self, blocking=True):
        """
        Acquire the lock.
        Acquire the mutex; acquire the lockfile.
        :param blocking: Wait for the lock.
        :type blocking: bool
        :return: self
        :rtype: Lock
        """
        self.__mutex.acquire(blocking)
        if self.__push() == 1:
            try:
                self.__lockf.acquire(blocking)
            except:
                self.__pop()
                raise
        return self

    def release(self):
        """
        Release the lock.
        Release the lockfile; release the mutex.
        """
        if self.__pop() == 0:
            self.__lockf.release()
        self.__mutex.release()
        return self

    def setpid(self, pid):
        """
        Write our procecss id and flush.
        :param pid: The process ID.
        :type pid: int
        """
        with self.__mutex:
            self.__lockf.setpid(pid)

    def __push(self):
        """
        Increment the lock depth.
        :return: The incremented depth
        :rtype: int
        """
        with self.__mutex:
            self.__depth += 1
            return self.__depth
            
    def __pop(self):
        """
        Decrement the lock depth.
        :return: The decremented depth
        :rtype: int
        """
        with self.__mutex:
            if self.__depth > 0:
                self.__depth -= 1
            return self.__depth

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, **unused):
        self.release()
