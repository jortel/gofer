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

import sys
from gofer.messaging import Queue
from gofer.messaging.base import Container
from gofer.messaging.producer import Producer
from gofer.messaging.window import *
from gofer.metrics import Timer
from gofer.proxy import Agent
from time import sleep
from datetime import datetime as dt
from datetime import timedelta as delta
from logging import INFO, basicConfig, getLogger
from threading import Thread
from agent import MyError

basicConfig(filename='/tmp/gofer/server.log', level=INFO)

log = getLogger(__name__)


def demo(agent):

    agent.__main__.echo('have a nice day')
    
    admin = agent.Admin()
    
    print admin.hello()
    
    cat = agent.Cat(secret='garfield')
    print cat.meow('PUR, auth worked!')
    try:
        cat = agent.Cat()
        cat.meow('hello')
    except:
        print 'Auth failed, damn cats.'

    try:
        # test bad return
        print cat.returnObject()
    except Exception, e:
        print e
        
    try:
        # test raise bad exception
        print cat.badException()
    except Exception, e:
        print e
    
    dog = agent.Dog()
    repolib = agent.RepoLib()
    print dog.bark('RUF')
    print dog.bark('hello')
    print dog.wag(3)
    print dog.bark('hello again')
    print repolib.update()
    try:
        print repolib.updated()
    except Exception, e:
        log.info('failed:', exc_info=True)
        print e
    try:
        print dog.notpermitted()
    except Exception, e:
        log.info('failed:', exc_info=True)
        print e
    try:
        print dog.keyError('jeff')
    except KeyError, e:
        log.info('failed:', exc_info=True)
        print e
    except Exception, e:
        log.info('failed:', exc_info=True)
        print e
    try:
        print dog.myError()
    except MyError, e:
        log.info('failed:', exc_info=True)
        print e
    except Exception, e:
        log.info('failed:', exc_info=True)
        print e


def later(**offset):
    return dt.utcnow()+delta(**offset)

def threads(uuid, n=10):
    for i in range(0,n):
        agent = Agent(uuid)
        name = 'Test%d' % i
        t = Thread(name=name, target=main, args=(uuid,))
        t.start()
        print 'thread: %s, started' % t.getName()
    return t

def perftest(uuid):
    N = 1000
    agent = Agent(uuid)
    dog = agent.Dog()
    t = Timer()
    t.start()
    print 'measuring performance ...'
    for i in range(0,N):
        dog.bark('performance!')
    t.stop()
    print 'total=%s, percall=%f (ms)' % (t, (t.duration()/N)*1000)
    sleep(10)

def main(uuid):
    tag = 'XYZ'

    agent = Agent(uuid)
    dog = agent.Dog(timeout=(3,10))
    print dog.sleep(1)

    # TTL
    agent = Agent(uuid, timeout=10)
    dog = agent.Dog()
    print dog.sleep(1)
    
    # synchronous
    print '(demo) synchronous'
    agent = Agent(uuid)
    timer = Timer()
    for i in range(0,10):
        timer.start()
        demo(agent)
        timer.stop()
        print '========= DEMO:%d [%s] ========' % (i, timer)
    #agent.delete()
    agent = None

    # asynchronous (fire and forget)
    print '(demo) asynchronous fire-and-forget'
    agent = Agent(uuid, async=True)
    demo(agent)

    # asynchronous
    print '(demo) asynchronous'
    window = Window(begin=dt.utcnow(), minutes=1)
    agent = Agent(uuid, ctag=tag, window=window)
    demo(agent)

    # asynchronous
    print '(demo) group asynchronous'
    group = (uuid, 'ABC',)
    window = Window(begin=dt.utcnow(), minutes=1)
    agent = Agent(group, ctag=tag)
    demo(agent)

    # future
    print 'maintenance window'
    dog = agent.Dog()

    # group 2
    print 'group 2'
    begin = later(seconds=20)
    window = Window(begin=begin, minutes=10)
    dog = agent.Dog(window=window, any='group 2')
    print dog.bark('hello')
    print dog.wag(3)
    print dog.bark('hello again')

    # group 1

    print 'group 1'
    begin = later(seconds=10)
    window = Window(begin=begin, minutes=10)
    dog = agent.Dog(window=window, any='group 1')
    print dog.bark('hello')
    print dog.wag(3)
    print dog.bark('hello again')

    agent = None

if __name__ == '__main__':
    uuid = 'xyz'
    if len(sys.argv) > 1:
        n = int(sys.argv[1])
        print '======= RUNNING %d THREADS ============' % n
        sleep(2)
        last = threads(uuid, n)
        last.join()
        sys.exit(0)
    for i in range(0,1000):
        print '======= %d ========' % i
        main(uuid)
    perftest(uuid)
    print 'finished.'


