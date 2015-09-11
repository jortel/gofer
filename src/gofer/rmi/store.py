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
Provides (local) message storage classes.
"""

import os

from time import sleep, time
from logging import getLogger
from Queue import Queue, Empty

from gofer import NAME, Thread, Singleton
from gofer.common import utf8
from gofer.common import mkdir, rmdir, unlink
from gofer.messaging import Document
from gofer.rmi.tracker import Tracker


log = getLogger(__name__)


class FileCorrupted(Exception):
    """
    File corrupted and likely discarded.
    """

    def __init__(self, path):
        super(FileCorrupted, self).__init__(path)

    @property
    def path(self):
        return self.args[0]

    def __str__(self):
        return "File %s corrupted.  Discarded" % self.path


class Pending(object):
    """
    Persistent store and queuing for pending requests.
    """

    __metaclass__ = Singleton

    PENDING = '/var/lib/%s/messaging/pending' % NAME

    # The queue depth
    MAX_DEPTH = 100000

    # The soft threshold determines when the journal
    # file path is queued instead of the actual request
    SOFT_THRESHOLD = 50

    @staticmethod
    def _write(request, path):
        """
        Write a request to the journal.
        :param request: An AMQP request.
        :type request: Document
        :param path: The destination path.
        :type path: str
        """
        fp = open(path, 'w+')
        try:
            body = request.dump()
            fp.write(body)
            log.debug('Writing [%s]: %s', path, body)
        finally:
            fp.close()

    @staticmethod
    def _read(path):
        """
        Read a request.
        :param path: The path to the journal file.
        :type path: str
        :return: The read request.
        :rtype: Document
        :raise FileCorrupted:
        """
        fp = open(path)
        try:
            try:
                request = Document()
                body = fp.read()
                request.load(body)
                log.debug('Read [%s]: %s', path, body)
                return request
            except ValueError:
                os.unlink(path)
                raise FileCorrupted(path)
        finally:
            fp.close()

    def _list(self):
        """
        Directory listing sorted by when it was created.
        :return: A sorted directory listing (absolute paths).
        :rtype: list
        """
        path = os.path.join(Pending.PENDING, self.stream)
        paths = [os.path.join(path, name) for name in os.listdir(path)]
        return sorted(paths)

    def __init__(self, stream, depth=MAX_DEPTH):
        """
        :param stream: The stream name.
        :type stream: str
        :param depth: The queue depth.
        :type depth: int
        """
        self.stream = stream
        self.queue = Queue(maxsize=depth)
        self.is_open = False
        self.sequential = Sequential()
        self.journal = {}
        self.thread = Thread(target=self._open)
        self.thread.setDaemon(True)
        self.thread.start()

    def _open(self):
        """
        Open for operations.
        Load journal(ed) requests. These are requests were in the queuing pipeline
        when the process was terminated. put() is blocked until this has completed.
        """
        path = os.path.join(Pending.PENDING, self.stream)
        mkdir(path)
        log.info('Using: %s', path)
        for path in self._list():
            log.info('Restoring: %s', path)
            try:
                request = Pending._read(path)
                self._put(request, path)
            except FileCorrupted, fe:
                log.debug(utf8(fe))
        self.is_open = True

    def put(self, request):
        """
        Enqueue a pending request.
        This is blocked until the _open() has re-queued journal(ed) entries.
        :param request: An AMQP request.
        :type request: Document
        """
        while not self.is_open:
            # block until opened
            sleep(1)
        fn = self.sequential.next()
        path = os.path.join(Pending.PENDING, self.stream, fn)
        Pending._write(request, path)
        self._put(request, path)

    def get(self):
        """
        Get the next pending request to be dispatched.
        Blocks until a request is available.
        :return: The next pending request.
        :rtype: Document
        """
        while not Thread.aborted():
            try:
                return self._get(timeout=10)
            except Empty:
                pass

    def commit(self, sn):
        """
        The request referenced by the serial number has been completely
        processed and can be deleted from the journal.
        :param sn: A request serial number.
        :param sn: str
        """
        try:
            path = self.journal[sn]
            unlink(path)
            log.debug('Request %s committed', sn)
        except KeyError:
            log.warn('Request %s not found for commit', sn)

    def delete(self):
        """
        Drain the queue and delete the store.
        """
        self.is_open = False
        self.thread.abort()
        self.thread.join()
        self._drain()
        path = os.path.join(Pending.PENDING, self.stream)
        rmdir(path)
        log.info('File %s deleted', path)

    def _drain(self):
        """
        Drain the queue.
        """
        self.is_open = False
        while not Thread.aborted():
            try:
                request = self._get(timeout=1)
                self.commit(request.sn)
            except Empty:
                break

    def _get(self, timeout=10):
        """
        Get the next pending request to be dispatched.
        The queued *thing* can be either a request or the path to
        a journal file.  When a path is detected, the file is read
        and the actual request is read.
        :return: The next pending request.
        :rtype: Document
        :raise Empty: when queue empty.
        """
        while True:
            if Thread.aborted():
                raise Empty()
            thing = self.queue.get(timeout=timeout)
            if isinstance(thing, str):
                try:
                    request = Pending._read(thing)
                except (IOError, OSError, FileCorrupted), fe:
                    log.warn(utf8(fe))
                    continue
            else:
                request = thing
            request.ts = time()
            return request

    def _put(self, request, jnl_path):
        """
        Enqueue the request.
        When the queue depth threshold is exceeded, the path to the
        journal file is queued instead of the actual request. This
        is done to reduce memory footprint for long backlogs.
        :param request: An AMQP request.
        :type request: Document
        :param jnl_path: Path to the associated journal file.
        :type jnl_path: str
        """
        tracker = Tracker()
        tracker.add(request.sn, request.data)
        self.journal[request.sn] = jnl_path
        if self.queue.qsize() > Pending.SOFT_THRESHOLD:
            thing = jnl_path
        else:
            thing = request
        self.queue.put(thing)


class Sequential(object):
    """
    Generate unique, sequential file names for journal entries.
    :ivar n: Appended to the new in the unlikely that subsequent calls
        to time() returns the same value.
    :type n: int
    :ivar last: The last time() value.
    :type last: float
    """

    FORMAT = '%f-%04d.json'

    def __init__(self):
        self.n = 0
        self.last = 0.0

    def next(self):
        """
        Get next (sequential) name to be used for the next journal file.
        :return: The next (sequential) name.
        :rtype: str
        """
        now = time()
        if now > self.last:
            self.n = 0
        else:
            self.n += 1
        self.last = now
        val = Sequential.FORMAT % (now, self.n)
        val = val.replace('.', '-', 1)
        return val
