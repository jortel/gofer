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

sys.path.insert(0, os.path.join(os.getcwd(), '../../src/'))

from random import random
from time import sleep
from threading import Thread
from gofer.metrics import Timer
from gofer.rmi.threadpool import ThreadPool
from unittest import TestCase

logging.basicConfig()


class Task:

    inst_list = []

    @classmethod
    def reset(cls):
        cls.inst_list = []

    @classmethod
    def all(cls):
        return cls.inst_list

    @classmethod
    def assert_called(cls, assert_true):
        for t in cls.inst_list:
            assert_true(t.called)

    def __init__(self, fn):
        self.fn  = fn
        self.called = False
        self.inst_list.append(self)

    def __call__(self, *args, **kwargs):
        self.called = True
        return self.fn(*args, **kwargs)


def fn(s):
    n = random()*3
    print 'sleep(%f)' % n
    sleep(n)
    return s.lower()

def fn2(s):
    print s
    return 'printed "%s"' % s

def exfn(s):
    n = random()*3
    print 'sleep(%f)' % n
    sleep(n)
    raise Exception(s)


def test_duplex(pool, fn, N=10):
    print 'START'
    t = Timer()
    t.start()
    reader = ReplyReader(pool, N)
    reader.start()
    for i in range(0,N):
        request = 'REQUEST-%d' % i
        pool.run(Task(fn), request)
    reader.join()
    t.stop()
    for r in reader.reply:
        print 'reply: %s' % str(r)
    print 'total: %s, per-call: %f' % (t, t.duration()/N)
    print repr(pool)

def test_simplex(pool, fn, N=3):
    for i in range(0,N):
        request = 'REQUEST-%d' % i
        pool.run(Task(fn), request)
    sleep(N)


class ReplyReader(Thread):

    def __init__(self, pool, n):
        Thread.__init__(self)
        self.reply = []
        self.pool = pool
        self.limit = n

    def run(self):
        for i in range(0, self.limit):
            r = self.pool.get()
            self.reply.append(r)
        print 'reply reader, finished'


class TestThreadPool(TestCase):

    def setUp(self):
        Task.reset()

    def test_basic_duplex(self):
        pool = ThreadPool(1, 10)
        for i in range(0, 100):
            id = pool.run(Task(fn2), 'hello')
            print pool.find(id)
        info = pool.info()
        self.assertEqual(info['pending'], 0)
        self.assertEqual(info['running'], 0)
        self.assertEqual(info['capacity'], 1)
        Task.assert_called(self.assertTrue)
        pool.shutdown()

    def test_duplex(self):
        pool = ThreadPool(1, 20)
        test_duplex(pool, fn2)
        test_duplex(pool, fn)
        test_duplex(pool, exfn)
        info = pool.info()
        self.assertEqual(info['pending'], 0)
        self.assertEqual(info['running'], 0)
        self.assertEqual(info['completed'], 0)
        self.assertEqual(info['capacity'], 10)
        Task.assert_called(self.assertTrue)
        pool.shutdown()

    def test_duplex_hard(self):
        pool = ThreadPool(1, 10)
        t1 = Thread(target=test_duplex, args=[pool, fn2, 1500])
        t2 = Thread(target=test_duplex, args=[pool, fn, 1500])
        t3 = Thread(target=test_duplex, args=[pool, exfn, 130])
        t1.start()
        t2.start()
        t3.start()
        t1.join()
        t2.join()
        t3.join()
        print repr(pool)
        pool.shutdown()

    def test_simplex(self):
        pool = ThreadPool(1, 10, duplex=False)
        test_simplex(pool, fn2)
        info = pool.info()
        self.assertEqual(info['pending'], 0)
        self.assertEqual(info['running'], 0)
        self.assertEqual(info['completed'], 0)
        Task.assert_called(self.assertTrue)
        pool.shutdown()


if __name__ == '__main__':
    pool = ThreadPool(1, 10)
    test_duplex(pool, fn)
    pool.shutdown()