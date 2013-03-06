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
from threading import Thread, RLock, Condition
from Queue import Queue, Empty
from logging import getLogger

from gofer import synchronized, conditional


log = getLogger(__name__)


class Worker(Thread):
    """
    Pool (worker) thread.
    @ivar pool: A thread pool.
    @type pool: L{ThreadPool}
    """
    
    def __init__(self, id, pool):
        """
        @param id: The worker id in the pool.
        @type id: int
        @param pool: A thread pool.
        @type pool: L{ThreadPool}
        """
        name = 'worker-%d' % id
        Thread.__init__(self, name=name)
        self.id = id
        self.pool = pool
        self.setDaemon(True)
        
    def run(self):
        """
        Main run loop; processes input queue.
        """
        while True:
            call = self.pool.pending()
            if not call:
                # exit requested
                self.pool = None
                return
            try:
                call(self.pool)
            except Exception:
                log.exception(str(call))


class Call:
    """
    A call to be executed by the thread pool.
    @ivar id: The unique call ID.
    @type id: str
    @ivar fn: The function/method to be executed.
    @type fn: callable
    @ivar args: The list of args passed to the callable.
    @type args: list
    @ivar kwargs: The list of keyword args passed to the callable.
    @type kwargs: dict
    """

    def __init__(self, id, fn, args=None, kwargs=None):
        """
        @param id: The unique call ID.
        @type id: str
        @param fn: The function/method to be executed.
        @type fn: callable
        @param args: The list of args passed to the callable.
        @type args: tuple
        @param kwargs: The list of keyword args passed to the callable.
        @type kwargs: dict
        """
        self.id = id
        self.fn = fn
        self.args = args or []
        self.kwargs = kwargs or {}
        self.retval = None

    def __call__(self, pool):
        """
        Execute the call.
        @param pool: A thread pool.
        @type pool: L{ThreadPool}
        """
        try:
            self.retval = self.fn(*self.args, **self.kwargs)
        except Exception, e:
            self.retval = e
        pool.completed(self)

    def __str__(self):
        s = ['call: ']
        s.append('%s = ' % self.retval)
        s.append(str(self.fn))
        s.append('(')
        s.append(str(self.args))
        s.append(', ')
        s.append(str(self.kwargs))
        s.append(')')
        return ''.join(s)


class IndexedQueue:
    """
    Synchronized call queue with indexed search.
    @ivar __condition: A condition used to synchronize the queue.
    @type __condition: L{Condition}
    @ivar __list: Provides fifo functionality.
    @type __list: list
    @ivar __dict: Provides indexed access.
    @type __dict: dict
    """

    def __init__(self):
        self.__condition = Condition()
        self.__list = []
        self.__dict = {}

    @conditional
    def put(self, call):
        """
        Put a call and retval in the queue.
        Signals threads waiting on the condition using get() or find().
        @param call: A call to enqueue.
        @type call: L{Call}
        """
        self.__list.insert(0, call)
        self.__dict[call.id] = call
        self.__notify()

    @conditional
    def get(self, blocking=True, timeout=None):
        """
        Read the next available call.
        @param blocking: Block and wait when the queue is empty.
        @type blocking: bool
        @param timeout: The time to wait when the queue is empty.
        @type timeout: int
        @return: The next completed call.
        @rtype: L{call}
        """
        waited = False
        while True:
            if self.__list:
                call = self.__list.pop()
                self.__dict.pop(call.id)
                return call
            else:
                if blocking:
                    if waited:
                        raise Empty()
                    self.__wait(timeout)
                    waited = True
                else:
                    raise Empty()

    @conditional
    def find(self, id, blocking=True, timeout=None):
        """
        Find a call result by ID.
        @param id: A call ID.
        @type id: str
        @param blocking: Block and wait when the queue is empty.
        @type blocking: bool
        @param timeout: The time to wait when the queue is empty.
        @type timeout: int
        @return: A completed call by call ID.
        @rtype: L{call}
        """
        waited = False
        while True:
            if self.__dict.has_key(id):
                call = self.__dict.pop(id)
                self.__list.remove(call)
                return call
            else:
                if blocking:
                    if waited:
                        raise Empty()
                    self.__wait(timeout)
                    waited = True
                else:
                    raise Empty()

    def __notify(self):
        self.__condition.notify_all()

    def __wait(self, timeout):
        self.__condition.wait(timeout)

    def __lock(self):
        self.__condition.acquire()

    def __unlock(self):
        self.__condition.release()

    @conditional
    def __len__(self):
        return len(self.__list)


class ThreadPool:
    """
    A load distributed thread pool.
    @ivar min: The min # of workers.
    @type min: int
    @ivar max: The max # of workers.
    @type max: int
    @ivar __pending: The worker pending queue.
    @type __pending: L{Queue}
    @ivar __threads: The list of workers
    @type __threads: list
    @ivar __tracking: The job tracking dict(s) (<pending>,<completed>)
    @type __tracking: tuple(2)
    @ivar __mutex: The pool mutex.
    @type __mutex: RLock
    """

    def __init__(self, min=1, max=1, duplex=True):
        """
        @param min: The min # of workers.
        @type min: int
        @param max: The max # of workers.
        @type max: int
        @param duplex: Indicates that the pool supports
            bidirectional communication.  That is, call
            results are queued. (default: True).
        @type duplex: bool
        """
        assert(min > 0)
        assert(max >= min)
        self.min = min
        self.max = max
        self.duplex = duplex
        self.__mutex = RLock()
        self.__pending = Queue()
        self.__threads = []
        self.__tracking = ({}, IndexedQueue())
        for x in range(0, min):
            self.__add()
        
    def run(self, fn, *args, **kwargs):
        """
        Schedule a call.
        Convenience method for scheduling.
        @param fn: A function/method to execute.
        @type fn: callable
        @param args: The args passed to fn()
        @type args: tuple
        @param kwargs: The keyword args passed fn()
        @type kwargs: dict
        @return The call ID.
        @rtype str
        """
        id = uuid4()
        call = Call(id, fn, args, kwargs)
        return self.schedule(call)

    def schedule(self, call):
        """
        Schedule a call.
        @param call: A call to schedule for execution.
        @param call: L{Call}
        @return: The call ID.
        @rtype: str
        """
        self.__expand()
        self.__track(call)
        self.__pending.put(call)
        return call.id

    def get(self, blocking=True, timeout=None):
        """
        Get the results of I{calls} executed in the pool.
        @param id: A job ID.
        @type id: str
        @param blocking: Block when queue is empty.
        @type blocking: bool
        @param timeout: The time (seconds) to block when empty.
        @return: Call result (call, retval)
        @rtype: tuple(2)
        """
        return self.__tracking[1].get(blocking, timeout)

    def find(self, id=None, blocking=True, timeout=None):
        """
        Find the results of I{calls} executed in the pool by job ID.
        @param id: A job ID.
        @type id: str
        @param blocking: Block when queue is empty.
        @type blocking: bool
        @param timeout: The time (seconds) to block when empty.
        @return: Call return value
        @rtype: object
        """
        return self.__tracking[1].find(id, blocking, timeout)

    def pending(self):
        """
        Used by worker to get the next pending call.
        @return: The next pending call.
        @rtype L{Call}
        """
        return self.__pending.get()

    def completed(self, call):
        """
        Result received.
        @param call: A call object.
        @type call: Call
        """
        if self.duplex:
            self.__tracking[1].put(call)
        self.__lock()
        try:
            self.__tracking[0].pop(call.id)
        finally:
            self.__unlock()

    def info(self):
        """
        Get pool statistics.
        @return: pool statistics
            - capacity: number of allocated threads
            - running: number of calls currently queued.
            - completed: number of calls completed but return has not been
                         consumed using get() or find().
        @rtype: dict
        """
        pending = self.__pending.qsize()
        self.__lock()
        try:
            return dict(
                capacity=len(self),
                pending=pending,
                running=len(self.__tracking[0]),
                completed=len(self.__tracking[1])
            )
        finally:
            self.__unlock()

    def shutdown(self):
        """
        Shutdown the pool.
        Terminate and join all workers.
        """
        # send stop request
        for n in range(0, len(self)):
            self.__pending.put(0)
        self.__lock()
        # safely copy list of threads
        try:
            threads = self.__threads[:]
            self.__threads = []
        finally:
            self.__unlock()
        # join stopped threads
        for t in threads:
            t.join()

    @synchronized
    def __track(self, call):
        """
        Call has been scheduled.
        @param call: A call (id, fn, args, kwargs).
        @type call: tuple(4)
        """
        self.__tracking[0][call.id] = call

    @synchronized
    def __add(self):
        """
        Add a thread to the pool.
        """
        total = len(self.__threads)
        if total < self.max:
            thread = Worker(total, self)
            self.__threads.append(thread)
            thread.start()

    @synchronized
    def __expand(self):
        """
        Expand the worker pool based on needed capacity.
        """
        total = len(self.__threads)
        queued = len(self.__tracking[0])
        capacity = (total-queued)
        if capacity < 1:
            self.__add()
    
    def __lock(self):
        self.__mutex.acquire()

    def __unlock(self):
        self.__mutex.release()

    @synchronized
    def __len__(self):
        return len(self.__threads)

    def __repr__(self):
        return 'pool: %s' % self.info()


class Immediate:
    """
    Run (immediate) pool.
    """
    
    def run(self, fn, *args, **options):
        """
        Run request.
        @param fn: A function/method to execute.
        @type fn: callable
        @param args: The args passed to fn()
        @type args: list
        @param options: The keyword args passed fn()
        @type options: dict
        """
        fn(*args, **options)
        return 0
