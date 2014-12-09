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

import os
import sys
import logging
import threading

from random import random
from time import sleep

sys.path.insert(0, os.path.join(os.getcwd(), '../../src/'))

from gofer.rmi.threadpool import ThreadPool


logging.basicConfig()


def fn1(n, results):
    t = threading.currentThread()
    delay = random() / 2
    print '%d) {%s} sleep(%f)' % (n, t.name, delay)
    sleep(delay)
    results.append(n)


def fn2(n, results):
    print str(n)
    results.append(n)


def test(calls=100):
    results = []
    pool = ThreadPool(9)
    for n in range(calls):
        pool.run(fn1, n, results)
    while len(results) < calls:
        sleep(1)
    print 'shutdown pool...'
    pool.shutdown()

if __name__ == '__main__':
    test()