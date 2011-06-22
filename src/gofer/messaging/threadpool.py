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
    """
    
    def __init__(self, number, pending, result):
        """
        @param number: The thread number in the pool.
        @type number: int
        @param pending: The pending queue.
        @type pending: L{Queue}
        @param result: The result queue.
        @type result: L{Queue}
        """
        name = 'worker-%d' % number
        Thread.__init__(self, name=name)
        self.pending = pending
        self.result = result
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
                fn = call[0]
                args = call[1]
                options = call[2]
                retval = fn(*args,**options)
            except Exception, e:
                retval = e
            result = (call, retval)
            self.result.put(result)


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
        self.__mutex = RLock()
        self.add(min)
        
    def run(self, fn, *args, **options):
        """
        Run request.
        @param fn: A function/method to execute.
        @type fn: callable
        @param args: The args passed to fn()
        @type args: list
        @param kwargs: The keyword args passed fn()
        @type kwargs: dict
        """
        call = (fn, args, options)
        self.__pending.put(call)
        self.__grow()
            
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
    
    def add(self, n=1):
        """
        Add the specified number of threads to the pool.
        The number added is limited by self.max.
        @param n: The number of threads to add.
        @type n: int
        """
        self.__lock()
        try:
            cnt = len(self.__threads)
            while n > 0 and cnt < self.max:
                t = Worker(cnt, self.__pending, self.__result)
                self.__threads.append(t)
                t.start()
                cnt += 1
                n -= 1
        finally:
            self.__unlock()
            
    def __grow(self):
        """
        Grow the pool based on needed capacity.
        """
        self.__lock()
        try:
            need = self.__pending.qsize()
            capacity = len(self.__threads)
            n = ( need - capacity )
            if n > 0:
                self.add(n)
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
        