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
from time import sleep
from gofer.messaging import Queue
from gofer.messaging.producer import Producer
from gofer.rmi.window import *
from gofer.rmi.dispatcher import *
from gofer.rmi.async import ReplyConsumer, WatchDog, Journal
from gofer.metrics import Timer
from gofer.proxy import Agent
from datetime import datetime as dt
from datetime import timedelta as delta
from logging import INFO, basicConfig, getLogger
from threading import Thread
from plugins import *

basicConfig(filename='/opt/gofer/server.log', level=INFO)

log = getLogger(__name__)

# asynchronous RMI timeout watchdog
watchdog = WatchDog()
watchdog.start()
#watchdog = Agent('xyz').WatchDog()


def onReply(reply):
    print 'REPLY [%s]\n%s' % (dt.now(), reply)
    
def isAsync(agent):
    options = agent._Container__options
    return (options.async or options.ctag)


def demo(agent):

    # module function
    agent.testplugin.echo('have a nice day')

    # admin hello
    admin = agent.Admin()
    print admin.hello()
    
    # misc synchronous
    dog = agent.Dog()
    repolib = agent.RepoLib()
    print dog.bark('RUF')
    print dog.bark('hello')
    print dog.wag(3)
    print dog.bark('hello again')
    print repolib.update()
    
    # test auth
    cat = agent.Cat(secret='garfield')
    print cat.meow('PUR, auth worked!')
    
    # test auth failed
    try:
        cat = agent.Cat()
        cat.meow('hello')
    except:
        print 'Auth failed, damn cats.'

    # bad return
    try:
        print cat.returnObject()
    except Exception, e:
        print e
        
    # raise bad exception
    try:
        print cat.badException()
    except Exception, e:
        print e

    # test MethodNotFound
    try:
        print repolib.updated()
    except Exception, e:
        log.info('failed:', exc_info=True)
        print e

    # test NotPermitted
    try:
        print dog.notpermitted()
    except Exception, e:
        log.info('failed:', exc_info=True)
        print e

    # test KeyError raised in plugin
    try:
        print dog.keyError('jeff')
    except KeyError, e:
        log.info('failed:', exc_info=True)
        print e
    except Exception, e:
        log.info('failed:', exc_info=True)
        print e

    # test custom Exception
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
        t.setDaemon(True)
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
    sys.exit(0)
    
def demoperftest(uuid, n=50):
    benchmarks = []
    print 'measuring performance using demo() ...'
    agent = Agent(uuid)
    timer = Timer()
    for i in range(0,n):
        timer.start()
        demo(agent)
        timer.stop()
        benchmarks.append(str(timer))
        print '========= DEMO:%d [%s] ========' % (i, timer)
    print 'benchmarks:'
    for t in benchmarks:
        print t
    del agent
    sys.exit(0)
    
def demoWatchdog(uuid):
    tag = uuid.upper()
    print '(watchdog) asynchronous'
    agent = Agent(uuid, ctag=tag)
    dog = agent.Dog(watchdog=watchdog, timeout=3, any='jeff')
    dog.bark('who you calling a watchdog?')
    dog.sleep(4)
    
def demoWindow(uuid, exit=0):
    tag = uuid.upper()
    print 'demo window, +10, +10min seconds'
    begin = later(seconds=10)
    window = Window(begin=begin, minutes=10)
    agent = Agent(uuid, ctag=tag)
    dog = agent.Dog(window=window, any='demo')
    print dt.now()
    print dog.bark('hello, after 10 seconds')
    print dog.wag(3)
    print dog.bark('hello again, after 10 seconds')
    sleep(12)
    if exit:
        sys.exit(0)
    
def demopam(uuid, yp, exit=0):
    agent = Agent(uuid)
    # basic success
    dog = agent.Dog(user='jortel', password=yp['jortel'])
    print dog.testpam()
    # @user synonym
    dog = agent.Dog(user='root', password=yp['root'])
    print dog.testpam2()
    # the @pam with specified service
    dog = agent.Dog(user='jortel', password=yp['jortel'])
    print dog.testpam3()
    # no user
    try:
        dog = agent.Dog()
        dog.testpam()
        raise Exception('Exception (UserRequired) expected')
    except UserRequired:
        print 'no user, OK'
    # no password
    try:
        dog = agent.Dog(user='jortel')
        dog.testpam()
        raise Exception('Exception (PasswordRequired) expected')
    except PasswordRequired:
        print 'no password, OK'
    # wrong user
    try:
        dog = agent.Dog(user='xx', password='xx')
        dog.testpam()
        raise Exception('Exception (UserNotAuthorized) expected')
    except UserNotAuthorized:
        print 'wrong user, OK'
    # PAM failed
    try:
        dog = agent.Dog(user='jortel', password='xx')
        dog.testpam()
        raise Exception('Exception (NotAuthenticated) expected')
    except NotAuthenticated:
        print 'PAM not authenticated, OK'
    # PAM failed, invalid service
    try:
        dog = agent.Dog(user='jortel', password='xx')
        dog.testpam4()
        raise Exception('Exception (NotAuthenticated) expected')
    except NotAuthenticated:
        print 'PAM not authenticated, invalid service, OK'
    if exit:
        sys.exit(0)
        
def demosecret(uuid, exit=0):
    uuid = ('dogfish', uuid)
    agent = Agent(uuid)
    # success
    cat = agent.Cat(secret='garfield')
    print cat.meow('secret, OK')
    # no secret
    try:
        cat = agent.Cat()
        cat.meow('secret, OK')
        raise Exception('Exception (SecretRequired) expected')
    except SecretRequired:
        print 'secret required, OK'
    # wrong secret
    try:
        cat = agent.Cat(secret='foo')
        cat.meow('secret, OK')
        raise Exception('Exception (SecretNotMatched) expected')
    except SecretNotMatched:
        print 'secret not matched, OK'
    if exit:
        sys.exit(0)
        
def demoauth(uuid, yp, exit=0):
    demosecret(uuid)
    demopam(uuid, yp)
    if exit:
        sys.exit(0)
        

def democonst(uuid, exit=0):
    agent = Agent(uuid)
    cowboy = agent.Cowboy()
    for name,age in (('jeff',10),('bart',45),):
        cowboy(name, age=age)
        print cowboy.howdy()
        assert(cowboy.name() == name)
        assert(cowboy.age() == age)
    try:
        cowboy = agent.Cowboy()
        print cowboy.howdy()
        raise Exception, 'Cowboy() should have failed.'
    except TypeError, e:
        pass
    if exit:
        sys.exit(0)
    

def main(uuid):
    tag = uuid.upper()

    # test timeout (not expired)
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
    demo(agent)

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

    # watchdog
    print '(watchdog) asynchronous'
    agent = Agent(uuid, ctag=tag)
    dog = agent.Dog(watchdog=watchdog, timeout=3, any='jeff')
    dog.bark('who you calling a watchdog?')
    dog.sleep(4)


if __name__ == '__main__':
    uuid = 'xyz'
    yp = {}
    yp['root'] = sys.argv[1]
    yp['jortel'] = sys.argv[2]
    demoauth(uuid, yp, 0)
    democonst(uuid)
    #perftest(uuid)
    #demoperftest(uuid)
    rcon = ReplyConsumer(Queue(uuid.upper()))
    rcon.start(onReply, watchdog=watchdog)
    #demoWindow(uuid)
    if len(sys.argv) > 3:
        n = int(sys.argv[3])
        print '======= RUNNING %d THREADS ============' % n
        sleep(2)
        last = threads(uuid, n)
        last.join()
        sys.exit(0)
    for i in range(0,100):
        print '======= %d ========' % i
        main(uuid)
    perftest(uuid)
    print 'finished.'


