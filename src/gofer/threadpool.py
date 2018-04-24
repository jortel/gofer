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
Thread Pool classes.
"""

from uuid import uuid4
from logging import getLogger
from queue import Queue, Empty

from gofer.compat import str
from gofer.common import Thread, released


log = getLogger(__name__)


class Worker(Thread):
    """
    Pool (worker) thread.
    :ivar queue: The work input queue..
    :type queue: Queue
    """

    HALT = 0
    
    def __init__(self, worker_id, queue):
        """
        :param worker_id: The worker id in the pool.
        :type worker_id: int
        """
        Thread.__init__(self, name='worker-%d' % worker_id)
        self.queue = queue
        self.setDaemon(True)

    @released
    def run(self):
        """
        Main run loop; processes input queue.
        """
        while not Thread.aborted():
            message = self.queue.get()
            if message == Worker.HALT:
                self.queue.put(message)
                return
            call = message
            try:
                call()
            except Exception:
                log.exception(str(call))


class Call(object):
    """
    A call to be executed by the thread pool.
    :ivar id: The unique call ID.
    :type id: str
    :ivar fn: The function/method to be executed.
    :type fn: callable
    :ivar args: The list of args passed to the callable.
    :type args: list
    :ivar kwargs: The list of keyword args passed to the callable.
    :type kwargs: dict
    """

    def __init__(self, fn, args=None, kwargs=None):
        """
        :param fn: The function/method to be executed.
        :type fn: callable
        :param args: The list of args passed to the callable.
        :type args: tuple
        :param kwargs: The list of keyword args passed to the callable.
        :type kwargs: dict
        """
        self.id = str(uuid4())
        self.fn = fn
        self.args = args or []
        self.kwargs = kwargs or {}

    def __call__(self):
        """
        Execute the call.
        """
        try:
            self.fn(*self.args, **self.kwargs)
        except Exception:
            log.exception(self.id)

    def __str__(self):
        s = list()
        s.append('call: ')
        s.append(str(self.fn))
        s.append('(')
        s.append(str(self.args))
        s.append(', ')
        s.append(str(self.kwargs))
        s.append(')')
        return ''.join(s)


class ThreadPool(object):
    """
    A load distributed thread pool.
    :ivar queue: The pool request queue.
    :type queue: Queue
    :ivar threads: List of: Worker
    :type threads: list
    """

    def __init__(self, capacity=1, backlog=100):
        """
        :param capacity: The # of workers.
        :type capacity: int
        :param backlog: Limit the queued calls.
        :type backlog: int
        """
        self.capacity = capacity
        self.queue = Queue(backlog)
        self.threads = []

    def start(self):
        """
        Start the pool.
        Populate the pool with started worker threads.
        """
        for worker_id in range(self.capacity):
            thread = Worker(worker_id, self.queue)
            self.threads.append(thread)
            thread.start()

    def run(self, fn, *args, **kwargs):
        """
        Schedule a call.
        Convenience method for scheduling.
        :param fn: A function/method to execute.
        :type fn: callable
        :param args: The args passed to fn()
        :type args: tuple
        :param kwargs: The keyword args passed fn()
        :type kwargs: dict
        :return The call ID.
        :rtype str
        """
        call = Call(fn, args, kwargs)
        self.queue.put(call)
        return call

    def shutdown(self, hard=False):
        """
        Shutdown the pool.
        Drain the queue, terminate and join all workers.
        :param hard: Abort threads in the pool.
            When not aborted, work in progress will attempt to
            be completed before shutdown.
        :type hard: bool
        :return: List of orphaned calls.  List of: Call.
        :rtype: list
        """
        drained = self.drain()
        if hard:
            for t in self.threads:
                t.abort()
        self.queue.put(Worker.HALT)
        for t in self.threads:
            if t == Thread.current():
                continue
            t.join()
        return drained

    def drain(self):
        """
        Drain the input queue.
        :return: List of drained calls.
        :rtype: list
        """
        drained = []
        while True:
            try:
                message = self.queue.get(block=False)
                if not isinstance(message, Call):
                    continue
                drained.append(message)
            except Empty:
                break
        return drained

    def __len__(self):
        return len(self.threads)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *unused):
        self.shutdown()

    def __repr__(self):
        description = [
            'pool:',
            'capacity=%d' % len(self),
            'queued: %d/%d' % (self.queue.qsize(), self.queue.maxsize)
        ]
        return ' '.join(description)


class Direct:
    """
    Call ignored (trashed).
    """

    def run(self, fn, *args, **options):
        """
        Run request.
        :param fn: A function/method to execute.
        :type fn: callable
        :param args: The args passed to fn()
        :type args: list
        :param options: The keyword args passed fn()
        :type options: dict
        """
        return fn(*args, **options)
