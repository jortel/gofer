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
from threading import Thread
from Queue import Queue
from logging import getLogger


log = getLogger(__name__)


class Worker(Thread):
    """
    Pool (worker) thread.
    :ivar queue: A thread pool worker.
    :type queue: Queue
    """
    
    def __init__(self, worker_id, backlog=100):
        """
        :param worker_id: The worker id in the pool.
        :type worker_id: int
        :param backlog: Limits the number of calls queued.
        :type backlog: int
        """
        name = 'worker-%d' % worker_id
        Thread.__init__(self, name=name)
        self.queue = Queue(backlog)
        self.setDaemon(True)
        
    def run(self):
        """
        Main run loop; processes input queue.
        """
        while True:
            call = self.queue.get()
            if not call:
                # termination requested
                return
            try:
                call()
            except Exception:
                log.exception(str(call))

    def put(self, call):
        """
        Enqueue a call.
        :param call: A call to queue.
        :type call: Call
        """
        self.queue.put(call)

    def backlog(self):
        """
        Get the number of call already queued to this worker.
        :return: The number of queued calls.
        :rtype: int
        """
        return self.queue.qsize()


class Call:
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

    def __init__(self, call_id, fn, args=None, kwargs=None):
        """
        :param call_id: The unique call ID.
        :type call_id: str
        :param fn: The function/method to be executed.
        :type fn: callable
        :param args: The list of args passed to the callable.
        :type args: tuple
        :param kwargs: The list of keyword args passed to the callable.
        :type kwargs: dict
        """
        self.id = call_id
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


class ThreadPool:
    """
    A load distributed thread pool.
    :ivar capacity: The min # of workers.
    :type capacity: int
    """

    def __init__(self, capacity=1):
        """
        :param capacity: The # of workers.
        :type capacity: int
        """
        self.capacity = capacity
        self.threads = []
        for x in range(capacity):
            self.__add()
        
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
        call_id = uuid4()
        call = Call(call_id, fn, args, kwargs)
        return self.schedule(call)

    def schedule(self, call):
        """
        Schedule a call.
        :param call: A call to schedule for execution.
        :param call: Call
        :return: The call ID.
        :rtype: str
        """
        pool = [(t.backlog(), t) for t in self.threads]
        pool.sort()
        backlog, worker = pool[0]
        worker.put(call)

    def shutdown(self):
        """
        Shutdown the pool.
        Terminate and join all workers.
        """
        # send stop request
        for t in self.threads:
            t.put(0)
        for t in self.threads:
            t.join()

    def __add(self):
        """
        Add a thread to the pool.
        """
        n = len(self.threads)
        thread = Worker(n)
        self.threads.append(thread)
        thread.start()

    def __len__(self):
        return len(self.threads)

    def __repr__(self):
        s = list()
        s.append('pool: capacity=%d' % self.capacity)
        for t in self.threads:
            s.append('worker: %s backlog: %d' % (t.name, t.backlog()))
        return '\n'.join(s)


class Trashed:
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
        pass
