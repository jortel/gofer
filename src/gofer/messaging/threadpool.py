#
# Copyright (c) 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
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
    @ivar pool: The containing pool.
    @type pool: L{ThreadPool}
    @ivar queue: The input queue.
    @type queue: L{Queue}
    """
    
    def __init__(self, name, pool):
        """
        @param name: The thread name.
        @type name: str
        @param pool: The containing pool.
        @type pool: L{ThreadPool}
        """
        Thread.__init__(self, name=name)
        self.pool = pool
        self.queue = Queue()
        self.setDaemon(True)
        
    def run(self):
        """
        Main run loop; processes input queue.
        """
        while True:
            call = self.queue.get()
            if not call:
                return
            try:
                fn, args, kwargs = call
                retval = fn(*args,**kwargs)
                self.pool.queue.put((call, retval))
            except Exception, e:
                print e
            self.pool.free(self)

    def enqueue(self, call):
        """
        Enqueue a call.
        @param call: A call to enqueue:
            (fn, *args, **kwargs)
        @type call: tuple
        """
        self.queue.put(call)
            
    def backlog(self):
        """
        Get the number of queued calls.
        @return: The qsize()
        @rtype: int
        """
        return self.queue.qsize()


class ThreadPool:
    """
    A load distributed thread pool.
    @ivar min: The min # of threads.
    @type min: int
    @ivar max: The max # of threads.
    @type max: int
    @ivar queue: The worker result queue.
    @type queue: L{Queue}
    @ivar __threads: The list of threads
    @type __threads: list
    @ivar __weight: The thread queue loading used for
        load distribution {id:[backlog,total]}
    @type __weight: dict
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
        self.queue = Queue()
        self.__threads = []
        self.__weight = {}
        self.__mutex = RLock()
        self.add(min)
        
    def run(self, fn, *args, **kwargs):
        """
        Run request.
        @param fn: A function/method to execute.
        @type fn: callable
        @param args: The args passed to fn()
        @type args: list
        @param kwargs: The keyword args passed fn()
        @type kwargs: dict
        """
        self.__lock()
        try:
            thread = self.next()
            self.busy(thread)
        finally:
            self.__unlock()
        call = (fn, args, kwargs)
        thread.enqueue(call)
            
    def busy(self, thread):
        """
        Increment the threads loading.
        @param thread: A worker thread
        @type thread: L{Worker}
        """
        self.__lock()
        try:
            key = id(thread)
            W = self.__weight[key]
            W[0] += 1
            W[1] += 1
            self.__weight[key] = W
        finally:
            self.__unlock()
            
    def free(self, thread):
        """
        Decrement the threads loading.
        @param thread: A worker thread
        @type thread: L{Worker}
        """
        self.__lock()
        try:
            key = id(thread)
            W = self.__weight[key]
            W[0] -= 1
            self.__weight[key] = W
        finally:
            self.__unlock()
            
    def shutdown(self):
        """
        Shutdown the pool and stop all threads.
        """
        self.__lock()
        try:
            for t in self.__threads:
                t.enqueue(0)
        finally:
            self.__unlock()
            
    def get(self, blocking=True, timeout=None):
        """
        Get the results of I{calls} executed in the pool.
        @param blocking: Block when queue is empty.
        @type blocking: bool
        @param timeout: The time (seconds) to block
            when the queue is empty.
        @return: Call result: (call, result)
        @rtype: tuple
        """
        try:
            return self.queue.get(blocking, timeout)
        except Empty:
            # normal
            pass
        
    def next(self):
        """
        Get the next thread to used for a call.
        The thread with the lowest weight (read backlog)
        is returned.  However, if that thread has a weight
        greater than 1, an attempt is made to add a new thread
        to the pool.  If added, the new thread is returned.
        @return: The lowest loaded thread.
        @rtype: L{Worker}
        """
        self.__lock()
        try:
            next = self.__threads[0]
            for t in self.__threads:
                if self.weight(t) < self.weight(next):
                    next = t
            if self.weight(next):
                added = self.add()
                if added:
                    return added[0]
            return next
        finally:
            self.__unlock()
            
    def weight(self, thread):
        """
        Get the weight (loading) of the specified thread.
        @param thread: A worker thread.
        @type thread: L{Worker}
        @return: The thread's current loading.
        @rtype: int
        """
        self.__lock()
        try:
            return self.__weight[id(thread)][0]
        finally:
            self.__unlock()
            
    def getload(self):
        """
        Get the loading (weight) of all threads.
        @return: list of: (tid, [weight,total]).
        @rtype: tuple
        """
        self.__lock()
        try:
            return self.__weight.items()
        finally:
            self.__unlock()
    
    def add(self, n=1):
        """
        Add the specified number of threads to the pool.
        The number added is limited by self.max.
        @param n: The number of threads to add.
        @type n: int
        @return: The list of added threads.
        @rtype: list
        """
        self.__lock()
        try:
            added = []
            for i in range(0, n):
                cnt = len(self.__threads)
                if cnt < self.max:
                    name = '-'.join(('worker', str(cnt)))
                    t = Worker(name, self)
                    self.__threads.append(t)
                    self.__weight[id(t)] = [0,0]
                    t.start()
                    added.append(t)
                else:
                    break
            return added
        finally:
            self.__unlock()
    
    def __lock(self):
        self.__mutex.acquire()

    def __unlock(self):
        self.__mutex.release()
        
    def __str__(self):
        self.__lock()
        try:
            s = []
            s.append('ThreadPool (%s): ' % id(self))
            s.append('min=%d' % self.min)
            s.append(', max=%d\n' % self.max)
            for t in self.__threads:
                w = self.__weight[id(t)]
                s.append('%s' % t.getName().ljust(10))
                s.append(' %s\n' % w)
            return ''.join(s)
        finally:
            self.__unlock()
        
        