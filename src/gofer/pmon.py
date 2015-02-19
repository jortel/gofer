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
from threading import RLock
from logging import getLogger
from time import sleep

from gofer import Thread, synchronized


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
    return 0


def digest(path):
    """
    Get the SHA256 hex digest for content.
    :param path: The absolute path to a file.
    :type path: str
    :return: the digest.
    :rtype: str
    """
    _hash = sha256()
    try:
        # file
        if os.path.isfile(path):
            fp = open(path)
            try:
                while True:
                    s = fp.read(10240)
                    if s:
                        _hash.update(s)
                    else:
                        break
            finally:
                fp.close()
        # directory
        else:
            for s in os.listdir(path):
                _hash.update(s)
        return _hash.hexdigest()
    except (IOError, OSError):
        pass
    return None


# --- monitor ----------------------------------------------------------------


class Tracker(object):
    """
    Path monitoring tracker.
    :ivar path: The absolute path to track.
    :type path: str
    :ivar last_modified: Last modified (m-time).
    :type last_modified: int
    :ivar digest: hex digest of file content.
    :type digest: str
    :ivar target: Called when path change detected.
    :type target: callable
    :ivar skip: The calls to skip due to prior call error.
    :type skip: int
    """

    def __init__(self, path, target):
        """
        :param path: The absolute path to track.
        :type path: str
        :param target: Called when path change detected.
        :type target: callable
        """
        self.path = path
        self.last_modified = last_modified(path)
        self.digest = digest(path)
        self.target = target
        self.skip = 0

    def __call__(self, last_modified, digest):
        """
        Called when path change detected.
        :param last_modified: Last modified (m-time).
        :type last_modified: int
        :param digest: hex digest of file content.
        :type digest: str
        """
        try:
            if self.skip:
                self.skip -= 1
                return
            self.target(self.path)
            self.last_modified = last_modified
            self.digest = digest
        except Exception, e:
            log.info('path: "%s" call raised: "%s"', self, e)
            self.skip = 30

    def __eq__(self, other):
        return self.path == other.path and self.target == other.target

    def __hash__(self):
        return hash((self.path, self.target))

    def __str__(self):
        return self.path


class PathMonitor(Thread):
    """
    Tracker monitor.
    :ivar _paths: A list of paths to monitor.
    :type _paths: list path:[last_modified, digest, target, skip]
    :ivar __mutex: The mutex.
    :type __mutex: RLock
    """

    def __init__(self, precision=1.0):
        super(PathMonitor, self).__init__()
        self.__mutex = RLock()
        self._precision = precision
        self._paths = set()
        self.setDaemon(True)

    @synchronized
    def add(self, path, target):
        """
        Add a path to be monitored.
        :param path: An absolute path to monitor.
        :type path: str
        :param target: Called when a change at path is detected.
        :type target: callable
        """
        self._paths.add(Tracker(path, target))

    @synchronized
    def delete(self, path, target):
        """
        Delete a path to be monitored.
        :param path: An absolute path to monitor.
        :type path: str
        :param target: Called when a change at path is detected.
        :type target: callable
        """
        try:
            self._paths.remove(Tracker(path, target))
        except KeyError:
            pass

    @synchronized
    def paths(self):
        """
        A cloned list of paths.
        :return: List of: Tracker.
        :rtype: list
        """
        return list(self._paths)

    def run(self):
        """
        Thread main.
        """
        delay = self._precision
        while not Thread.aborted():
            sleep(delay)
            for tracker in self.paths():
                self._sniff(tracker)

    def _sniff(self, tracker):
        """
        Sniff the path.
          1. diff file modified times.
          2. diff file hash.
          3. target()
        :param tracker: A path to sniff.
        :type tracker: Tracker
        """
        path = tracker.path
        _last_modified = last_modified(path)
        if _last_modified == tracker.last_modified:
            # not touched
            return
        _digest = digest(path)
        if _digest == tracker.digest:
            # unchanged
            return
        tracker(_last_modified, _digest)
