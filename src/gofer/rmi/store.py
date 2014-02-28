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
import errno

from stat import *
from time import sleep, time
from threading import Thread
from Queue import Queue
from logging import getLogger

from gofer import NAME, Singleton
from gofer.messaging.model import Envelope
from gofer.rmi.window import Window
from gofer.rmi.tracker import Tracker


log = getLogger(__name__)


class Pending(object):
    """
    Persistent store and queuing for pending requests.
    """

    __metaclass__ = Singleton

    PENDING = '/var/lib/%s/messaging/pending' % NAME
    DELAYED = '/var/lib/%s/messaging/delayed' % NAME

    @staticmethod
    def _created(path):
        """
        Get create timestamp.
        :return: The file create timestamp.
        :rtype: int
        """
        stat = os.stat(path)
        return stat[ST_CTIME]

    @staticmethod
    def _mkdir(path):
        """
        Ensure the directory exists.
        :param: A directory path.
        :type path: str
        """
        try:
            os.makedirs(path)
        except OSError, e:
            if e.errno != errno.EEXIST:
                raise

    @staticmethod
    def _write(request, path):
        """
        Write a request to the journal.
        :param request: An AMQP request.
        :type request: Envelope
        :param path: The destination path.
        :type path: str
        """
        fp = open(path, 'w+')
        try:
            body = request.dump()
            fp.write(body)
            log.debug('wrote [%s]:\n%s', path, body)
        finally:
            fp.close()

    @staticmethod
    def _read(path):
        """
        Read a request.
        :param path: The path to the journal file.
        :type path: str
        :return: The read request.
        :rtype: Envelope
        """
        fp = open(path)
        try:
            try:
                request = Envelope()
                body = fp.read()
                request.load(body)
                log.debug('read [%s]:\n%s', path, body)
                return request
            except ValueError:
                log.error('%s corrupt (discarded)', path)
                os.unlink(path)
        finally:
            fp.close()

    @staticmethod
    def _delayed(request):
        """
        Get whether the envelope has a future window.
        Cancelled requests are not considered to be delayed and
        the window is ignored.
        :param request: An AMQP request.
        :type request: Envelope
        :return: True when window in the future.
        :rtype: bool
        """
        tracker = Tracker()
        if request.window and not tracker.cancelled(request.sn):
            window = Window(request.window)
            if window.future():
                log.debug('%s delayed', request.sn)
                return True
        return False

    @staticmethod
    def commit(sn):
        """
        The request referenced by the serial number has been completely
        processed and can be deleted from the journal.
        :param sn: A request serial number.
        :param sn: str
        """
        try:
            path = os.path.join(Pending.PENDING, sn)
            os.unlink(path)
            log.debug('%s committed', sn)
        except OSError, e:
            if e.errno != errno.ENOENT:
                raise

    @staticmethod
    def _list(path):
        """
        Directory listing sorted by when it was created.
        :param path: The path to a directory.
        :type path: str
        :return: A sorted directory listing (absolute paths).
        :rtype: list
        """
        paths = []
        _dir = path
        for path in [os.path.join(_dir, name) for name in os.listdir(_dir)]:
            paths.append((Pending._created(path), path))
        paths.sort()
        return [p[1] for p in paths]

    def __init__(self, backlog=100):
        """
        :param backlog: The queue capacity.
        :type backlog: int
        """
        Pending._mkdir(Pending.PENDING)
        Pending._mkdir(Pending.DELAYED)
        self.queue = Queue(backlog)
        self.is_open = False
        self.thread = Thread(target=self._open)
        self.thread.setDaemon(True)
        self.thread.start()

    def _open(self):
        """
        Open for operations.
        - Load journal(ed) requests. These are requests were in the queuing pipeline
          when the process was terminated. put() is blocked until this has completed.
        - Then, continuously attempt to queue delayed messages.
        """
        for path in Pending._list(Pending.PENDING):
            request = Pending._read(path)
            if not request:
                # read failed
                continue
            request.ts = time()
            self.queue.put(request)
        self.is_open = True
        # queue delayed messages
        while True:
            sleep(1)
            for path in Pending._list(Pending.DELAYED):
                request = Pending._read(path)
                if not request:
                    # read failed
                    continue
                if Pending._delayed(request):
                    continue
                self.put(request)
                os.unlink(path)

    def put(self, request):
        """
        Enqueue a pending request.
        This is blocked until the _open() has re-queued journal(ed) entries.
        :param request: An AMQP request.
        :type request: Envelope
        """
        while not self.is_open:
            # block puts until opened
            sleep(1)

        if not Pending._delayed(request):
            path = os.path.join(Pending.PENDING, request.sn)
            Pending._write(request, path)
            tracker = Tracker()
            tracker.add(request.sn, request.any)
            request.ts = time()
            self.queue.put(request)
        else:
            path = os.path.join(Pending.DELAYED, request.sn)
            Pending._write(request, path)

    def get(self):
        """
        Get the next pending request to be dispatched.
        Blocks until a request is available.
        :return: The next pending request.
        :rtype: Envelope
        """
        return self.queue.get()

