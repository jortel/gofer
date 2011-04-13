#! /usr/bin/env python
#
# Copyright (c) 2010 Red Hat, Inc.
#
# Authors: Jeff Ortel <jortel@redhat.com>
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

from random import random
from time import sleep
from gofer.metrics import Timer
from gofer.messaging.threadpool import ThreadPool

def fn(s):
    n = random()*5
    print 'sleep(%d)' % n
    sleep(n)
    return s.lower()

if __name__ == '__main__':
    pool = ThreadPool('test', 1,10)
    N = 100
    print 'START'
    t = Timer()
    t.start()
    for i in range(0,N):
        request = 'REQUEST-%d' % i
        pool.run(fn, request)
    for i in range(0,N):
        print pool.get()
    t.stop()
    print 'total: %s, per-call: %f' % (t, t.duration()/N)
    for w in pool.getload():
        print w
