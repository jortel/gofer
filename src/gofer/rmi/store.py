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
from queue import Queue, Empty

from gofer import NAME, Thread
from gofer.common import mkdir, rmdir, unlink
from gofer.messaging import Document
from gofer.rmi.tracker import Tracker


log = getLogger(__name__)


class Pending(object):
    """
    Persistent store and queuing for pending requests.
    """

    PENDING = '/var/lib/%s/messaging/pending' % NAME

    @staticmethod
    def _write(request, path):
        """
        Write a request to the journal.
        :param request: An AMQP request.
        :type request: Document
        :param path: The destination path.
        :type path: str
        """
        with open(path, 'w+') as fp:
            body = request.dump()
            fp.write(body)
            log.debug('wrote [%s]: %s', path, body)

    @staticmethod
    def _read(path):
        """
        Read a request.
        :param path: The path to the journal file.
        :type path: str
        :return: The read request.
        :rtype: Document
        """
        with open(path) as fp:
            try:
                request = Document()
                body = fp.read()
                request.load(body)
                log.debug('read [%s]: %s', path, body)
                return request
            except ValueError:
                log.error('%s corrupt (discarded)', path)
                unlink(path)

    def _list(self):
        """
        Directory listing sorted by when it was created.
        :return: A sorted directory listing (absolute paths).
        :rtype: list
        """
        path = os.path.join(Pending.PENDING, self.stream)
        paths = [os.path.join(path, name) for name in os.listdir(path)]
        return sorted(paths)

    def __init__(self, stream):
        """
        :param stream: The stream name.
        :type stream: str
        """
        self.stream = stream
        self.queue = Queue(maxsize=100)
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
            request = Pending._read(path)
            if not request:
                # read failed
                continue
            self._put(request, path)
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
        :raise Empty: on thread aborted.
        """
        while not Thread.aborted():
            try:
                return self.queue.get(timeout=10)
            except Empty:
                pass
        # aborted
        raise Empty()

    def commit(self, sn):
        """
        The request referenced by the serial number has been completely
        processed and can be deleted from the journal.
        :param sn: A request serial number.
        :param sn: str
        """
        try:
            path = self.journal.pop(sn)
            unlink(path)
            log.debug('%s committed', sn)
        except KeyError:
            log.warning('%s not found for commit', sn)

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
        log.info('%s, deleted', path)

    def _drain(self):
        """
        Drain the queue.
        """
        self.is_open = False
        while not Thread.aborted():
            try:
                request = self.queue.get(timeout=1)
                self.commit(request.sn)
            except Empty:
                break

    def _put(self, request, jnl_path):
        """
        Enqueue the request.
        :param request: An AMQP request.
        :type request: Document
        :param jnl_path: Path to the associated journal file.
        :type jnl_path: str
        """
        request.ts = time()
        tracker = Tracker()
        tracker.add(request.sn, request.data)
        self.journal[request.sn] = jnl_path
        self.queue.put(request)


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
