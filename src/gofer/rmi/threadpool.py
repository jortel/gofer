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

from threading import Thread, RLock
from Queue import Queue, Empty
from time import sleep


class Worker(Thread):
    """
    Pool (worker) thread.
    @ivar pending: The worker pending queue.
    @type pending: L{Queue}
    @ivar result: The worker result queue.
    @type result: L{Queue}
    @ivar busy: mark busy function.
    @type busy: callable
    @ivar free: mark free function.
    @type free: callable
    """
    
    def __init__(self, id, pending, result, busy, free):
        """
        @param id: The thread id in the pool.
        @type id: int
        @param pending: The pending queue.
        @type pending: L{Queue}
        @param result: The result queue.
        @type result: L{Queue}
        @param busy: mark busy function.
        @type busy: callable
        @param free: mark free function.
        @type free: callable
        """
        name = 'worker-%d' % id
        Thread.__init__(self, name=name)
        self.id = id
        self.pending = pending
        self.result = result
        self.busy = busy
        self.free = free
        self.setDaemon(True)
        
    def run(self):
        """
        Main run loop; processes input queue.
        """
        while True:
            call = self.pending.get()
            if not call:
                # exit requested
                return
            try:
                self.busy(self.id)
                fn = call[0]
                args = call[1]
                options = call[2]
                retval = fn(*args,**options)
            except Exception, e:
                retval = e
            result = (call, retval)
            self.result.put(result)
            self.free(self.id)


class ThreadPool:
    """
    A load distributed thread pool.
    @ivar min: The min # of threads.
    @type min: int
    @ivar max: The max # of threads.
    @type max: int
    @ivar __pending: The worker pending queue.
    @type __pending: L{Queue}
    @ivar __result: The worker result queue.
    @type __result: L{Queue}
    @ivar __threads: The list of threads
    @type __threads: list
    @ivar __busy: The set of busy thread ids.
    @type __busy: set
    @ivar __mutex: The pool mutex.
    @type __mutex: RLock
    """

    def __init__(self, min=1, max=1):
        """
        @param min: The min # of threads.
        @type min: int
        @param max: The max # of threads.
        @type max: int
        """
        assert(min > 0)
        assert(max >= min)
        self.min = min
        self.max = max
        self.__pending = Queue()
        self.__result = Queue()
        self.__threads = []
        self.__busy = set()
        self.__mutex = RLock()
        for x in range(0, min):
            self.__add()
        
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
        self.__grow()
        call = (fn, args, options)
        self.__pending.put(call)
            
    def get(self, blocking=True, timeout=None):
        """
        Get the results of I{calls} executed in the pool.
        @param blocking: Block when queue is empty.
        @type blocking: bool
        @param timeout: The time (seconds) to block when empty.
        @return: Call result: (call, result)
        @rtype: tuple
        """
        try:
            return self.__result.get(blocking, timeout)
        except Empty:
            # normal
            pass
    
    def __add(self):
        """
        Add a thread to the pool.
        """
        self.__lock()
        try:
            total = len(self.__threads)
            if total == self.max:
                return
            thread = Worker(
                total,
                self.__pending,
                self.__result,
                self.__markbusy,
                self.__markfree)
            self.__threads.append(thread)
            thread.start()
        finally:
            self.__unlock()
            
    def __markbusy(self, id):
        """
        Mark a worker thread I{busy}.
        @param id: A worker thread id.
        @type id: str
        """
        self.__lock()
        try:
            self.__busy.add(id)
        finally:
            self.__unlock()
            
    def __markfree(self, id):
        """
        Mark a worker thread I{free}.
        @param id: A worker thread id.
        @type id: str
        """
        self.__lock()
        try:
            if id in self.__busy:
                self.__busy.remove(id)
        finally:
            self.__unlock()
            
    def __grow(self):
        """
        Grow the pool based on needed capacity.
        """
        self.__lock()
        try:
            backlog = self.__pending.qsize()
            total = len(self.__threads)
            busy = len(self.__busy)
            capacity = (total-busy)
            if capacity == 0:
                self.__add()
        finally:
            self.__unlock()
    
    def __lock(self):
        self.__mutex.acquire()

    def __unlock(self):
        self.__mutex.release()
    
    def __len__(self):
        self.__lock()
        try:
            return len(self.__threads)
        finally:
            self.__unlock()
        
    def __del__(self):
        n = len(self.__threads)
        while n > 0:
            self.__pending.put(0)
            n -= 1


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
        return fn(*args, **options)