#
# Copyright (c) 2017 Red Hat, Inc.
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

import os
import sys

from logging import getLogger
from threading import RLock
from time import sleep

from gofer import Thread, utf8, synchronized
from gofer.rmi.context import Context
from gofer.rmi.model import protocol
from gofer.mp import PipeBroken, Writer as _Writer

log = getLogger(__name__)


class Call(protocol.Call):
    """
    The child-side of the forked call.
    """

    @staticmethod
    def _not_cancelled():
        return False

    def __call__(self, pipe):
        """
        Perform RMI on the child-side of the forked call
        as follows:
          - Reset the RMI context.
          - Invoke the method
          - Send result: retval, progress, raised exception.
        All output is sent to the parent using the inter-process pipe.
        :param pipe: A message pipe.
        :type  pipe: gofer.mp.Pipe
        """
        pipe.writer = Writer(pipe.writer.fd)
        try:
            pipe.reader.close()
            monitor = ParentMonitor(pipe.writer)
            monitor.start()
            context = Context.current()
            context.cancelled = self._not_cancelled()
            context.progress = Progress(pipe.writer)
            result = self.method(*self.args, **self.kwargs)
            reply = protocol.Result(result)
            reply.send(pipe.writer)
        except PipeBroken:
            log.debug('Pipe broken.')
        except Exception, e:
            log.exception(utf8(e))
            reply = protocol.Raised(e)
            reply.send(pipe.writer)


class Writer(_Writer):
    """
    A thread-safe *writing* end of a Pipe.
    """

    def __init__(self, fd):
        """
        :param fd: An open pipe file descriptor.
        :type fd: int
        """
        super(Writer, self).__init__(fd)
        self.__mutex = RLock()

    @synchronized
    def put(self, thing):
        """
        Pickle and write the object into the pipe.
        :param thing: An object.
        :type thing: any
        """
        super(Writer, self).put(thing)


class Progress(object):
    """
    Provides progress reporting to the parent through the pipe.
    :ivar pipe: A message pipe.
    :type pipe: gofer.mp.Writer
    :ivar total: The total work units.
    :type total: int
    :ivar completed: The completed work units.
    :type completed: int
    :ivar details: The reported details.
    :type details: object
    """

    def __init__(self, pipe):
        """
        :param pipe: A message pipe.
        :type  pipe: gofer.mp.Writer
        """
        self.pipe = pipe
        self.total = 0
        self.completed = 0
        self.details = {}

    def report(self):
        """
        Report progress.
        """
        payload = protocol.ProgressPayload(
            total=self.total,
            completed=self.completed,
            details=self.details)
        reply = protocol.Progress(payload)
        reply.send(self.pipe)


class ParentMonitor(Thread):
    """
    Parent process monitor.
    Send a PING periodically expecting a broken pipe if the parent has terminated.
    :ivar pipe: A message pipe.
    :type  pipe: gofer.mp.Writer
    :ivar pid: This process ID.
    :type pid: int
    """

    # ping interval (seconds)
    INTERVAL = 1.0

    def __init__(self, pipe):
        """
        :param pipe: A message pipe.
        :type  pipe: gofer.mp.Writer
        """
        super(ParentMonitor, self).__init__(name='parent-monitor')
        self.pid = os.getpid()
        self.pipe = pipe

    def run(self):
        while not Thread.aborted():
            sleep(self.INTERVAL)
            try:
                reply = protocol.Ping(self.pid)
                reply.send(self.pipe)
            except PipeBroken:
                sys.exit(1)
