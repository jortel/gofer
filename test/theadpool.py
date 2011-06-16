#! /usr/bin/env python
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

from random import random
from time import sleep
from threading import Thread
from gofer.metrics import Timer
from gofer.messaging.threadpool import ThreadPool

class ReplyReader(Thread):
    
    def __init__(self, pool, n):
        Thread.__init__(self)
        self.reply = []
        self.pool = pool
        self.limit = n
    
    def run(self):
        for i in range(0, self.limit):
            r = pool.get()
            self.reply.append(r)


def fn(s):
    n = random()*3
    print 'sleep(%d)' % n
    sleep(n)
    raise Exception(s)
    return s.lower()

def exfn(s):
    n = random()*3
    print 'sleep(%d)' % n
    sleep(n)
    raise Exception(s)

def test(pool, fn):
    N = 100
    print 'START'
    t = Timer()
    t.start()
    reader = ReplyReader(pool, N)
    reader.start()
    for i in range(0,N):
        request = 'REQUEST-%d' % i
        pool.run(fn, request)
    reader.join()
    t.stop()
    for r in reader.reply:
        print r
    print 'total: %s, per-call: %f' % (t, t.duration()/N)
    print repr(pool)

if __name__ == '__main__':
    pool = ThreadPool(1,10)
    test(pool, fn)
    test(pool, exfn)
