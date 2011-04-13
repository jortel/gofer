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

from threading import Thread, RLock
from Queue import Queue, Empty
from time import sleep



class Worker(Thread):
    
    def __init__(self, name, pool):
        Thread.__init__(self, name=name)
        self.pool = pool
        self.queue = Queue()
        self.setDaemon(True)
        
    def run(self):
        while True:
            call = self.queue.get()
            if not call:
                return
            try:
                self.queue.task_done()
                fn, args, kwargs = call
                retval = fn(*args,**kwargs)
                self.pool.queue.put((call, retval))
            except Exception, e:
                print e
            self.pool.free(self)

    def enqueue(self, call):
        self.queue.put(call)
            
    def backlog(self):
        return self.queue.qsize()


class ThreadPool:

    def __init__(self, name, min=1, max=1):
        assert(min > 0)
        assert(max >= min)
        self.name = name
        self.min = min
        self.max = max
        self.queue = Queue()
        self.__threads = []
        self.__weight = {}
        self.__mutex = RLock()
        self.add(min)
        
    def run(self, fn, *args, **kwargs):
        self.__lock()
        try:
            t = self.next()
            call = (fn, args, kwargs)
            self.busy(t)
            t.enqueue(call)
        finally:
            self.__unlock()
            
    def busy(self, thread):
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
        self.__lock()
        try:
            key = id(thread)
            W = self.__weight[key]
            W[0] -= 1
            self.__weight[key] = W
        finally:
            self.__unlock()
            
    def shutdown(self):
        self.__lock()
        try:
            for t in self.__threads:
                t.enqueue(0)
        finally:
            self.__unlock()
            
    def get(self, blocking=True, timeout=None):
        try:
            return self.queue.get(blocking, timeout)
        except Empty:
            # normal
            pass
        
    def next(self):
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
        self.__lock()
        try:
            return self.__weight[id(thread)][0]
        finally:
            self.__unlock()
            
    def getload(self):
        self.__lock()
        try:
            return self.__weight.items()
        finally:
            self.__unlock()
    
    def add(self, n=1):
        self.__lock()
        try:
            added = []
            for i in range(0, n):
                cnt = len(self.__threads)
                if cnt < self.max:
                    name = '-'.join((self.name, str(cnt)))
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
        