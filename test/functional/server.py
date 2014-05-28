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
from optparse import OptionParser, Option
from hashlib import sha256
from datetime import datetime as dt
from datetime import timedelta as delta
from logging import DEBUG, INFO, basicConfig, getLogger
from threading import Thread

from gofer.rmi.window import *
from gofer.rmi.dispatcher import *
from gofer.rmi.async import ReplyConsumer
from gofer.metrics import Timer
from gofer.proxy import Agent as RealAgent
from gofer.messaging import Queue
from gofer.messaging.auth import Authenticator, ValidationFailed

from plugins import *

basicConfig(filename='/opt/gofer/server.log')

log = getLogger(__name__)

getLogger('gofer.transport').setLevel(DEBUG)


class Agent(object):

    base_options = {}

    def __new__(cls, *args, **options):
        all_options = dict(Agent.base_options)
        all_options.update(options)
        return RealAgent(*args, **all_options)


class TestAuthenticator(Authenticator):

    def sign(self, message):
        h = sha256()
        h.update(message)
        digest = h.hexdigest()
        # print 'signed: %s' % digest
        return digest

    def validate(self, document, message, signature):
        digest = self.sign(message)
        valid = signature == digest
        # print 'matching signatures: [%s, %s]' % (signature, digest)
        if valid:
            return
        raise ValidationFailed(
            'matching signatures: [%s, %s]' % (signature, digest))


class ListOption(Option):
    ACTIONS = Option.ACTIONS + ('extend',)
    STORE_ACTIONS = Option.STORE_ACTIONS + ('extend',)
    TYPED_ACTIONS = Option.TYPED_ACTIONS + ('extend',)
    ALWAYS_TYPED_ACTIONS = Option.ALWAYS_TYPED_ACTIONS + ('extend',)

    def take_action(self, action, dest, opt, value, values, parser):
        if action == 'extend':
            values.ensure_value(dest, []).append(value)
        else:
            Option.take_action(self, action, dest, opt, value, values, parser)


def on_reply(reply):
    print 'REPLY [%s]\n%s' % (dt.now(), reply)


def demo(agent):

    # module function
    agent.testplugin.echo('have a nice day')

    # admin hello
    admin = agent.Admin()
    print admin.hello()
    
    # misc
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
    t = None
    for i in range(0, n):
        name = 'Test%d' % i
        t = Thread(name=name, target=main, args=(uuid,))
        t.setDaemon(True)
        t.start()
        print 'thread: %s, started' % t.getName()
    return t


def test_performance(uuid):
    N = 200
    agent = Agent(uuid)
    dog = agent.Dog()
    t = Timer()
    t.start()
    print 'measuring performance ...'
    for i in range(0,N):
        dog.bark('performance!')
    t.stop()
    print 'total=%s, percall=%f (ms)' % (t, (t.duration()/N)*1000)
    #sys.exit(0)
    # ASYNCHRONOUS
    dog = agent.Dog(async=1)
    t = Timer()
    t.start()
    print 'measuring (async) performance ...'
    for i in range(0,N):
        dog.bark('performance!')
    t.stop()
    print 'total=%s, percall=%f (ms)' % (t, (t.duration()/N)*1000)
    sys.exit(0)


def test_triggers(uuid):
    agent = Agent(uuid)
    dog = agent.Dog(trigger=1)
    t = dog.bark('delayed!')
    print t
    t()
    # broadcast
    agent = Agent([uuid,])
    dog = agent.Dog(trigger=1)
    for t in dog.bark('delayed!'):
        print t
        t()
    print 'Manual trigger, OK'
    

def demotest_performance(uuid, n=50):
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


def demo_window(uuid, exit=0):
    tag = uuid.upper()
    print 'demo window, +10, +10min seconds'
    begin = later(seconds=10)
    window = Window(begin=begin, seconds=5)
    agent = Agent(uuid, ctag=tag)
    dog = agent.Dog(window=window, any='demo')
    print dt.now()
    print dog.bark('hello, after 10 seconds')
    print dog.wag(3)
    print dog.bark('hello again, after 10 seconds')
    sleep(120)
    if exit:
        sys.exit(0)
    

def demo_pam_authentication(uuid, yp, exit=0):
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


def demo_layered_security(uuid, yp, exit=0):
    agent = Agent(uuid)
    # multi-user
    for user in ('jortel', 'root'):
        dog = agent.Dog(user=user, password=yp[user])
        print dog.testLayered()
    # mixed user and secret
    dog = agent.Dog(user=user, password=yp[user])
    print dog.testLayered2()
    dog = agent.Dog(secret='elmer')
    print dog.testLayered2()
    try:
        dog = agent.Dog()
        print dog.testLayered2()
        raise Exception('Exception (UserRequired) expected')
    except UserRequired:
        pass
    if exit:
        sys.exit(0)

        
def demo_shared_secret(uuid, exit=0):
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
        

def demo_authentication(uuid, yp, exit=0):
    demo_shared_secret(uuid)
    demo_pam_authentication(uuid, yp)
    demo_layered_security(uuid, yp)
    if exit:
        sys.exit(0)


def demo_constructors(uuid, exit=0):
    agent = Agent(uuid)
    cowboy = agent.Cowboy()
    for name,age in (('jeff', 10), ('bart', 45),):
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
        
        
def demo_getitem(uuid, exit=0):
    agent = Agent(uuid)
    fn = agent['Dog']['bark']
    print fn('RUF')
    if exit:
        sys.exit(0)
        

def demo_progress(uuid, exit=0):
    # synchronous
    def fn(report):
        pct = (float(report['completed'])/float(report['total']))*100
        print 'Progress: sn=%s, any=%s, total=%s, complete=%s, pct:%d%% details=%s' % \
            (report['sn'],
             report['any'],
             report['total'],
             report['completed'],
             int(pct),
             report['details'])
    agent = Agent(uuid)
    p = agent.Progress(progress=fn, any={4:5})
    print p.send(4)
    if exit:
        sys.exit(0)
    

def main(uuid):
    tag = uuid.upper()

    # test timeout (not expired)
    agent = Agent(uuid)
    dog = agent.Dog(timeout=3)
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
    agent = Agent(uuid, async=True, url=url)
    demo(agent)

    # asynchronous
    print '(demo) asynchronous'
    window = Window(begin=dt.utcnow(), minutes=1)
    agent = Agent(uuid, ctag=tag, window=window)
    demo(agent)

    # asynchronous
    print '(demo) group asynchronous'
    group = (uuid, uuid)
    window = Window(begin=dt.utcnow(), minutes=1)
    agent = Agent(group, ctag=tag, window=window)
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


def smoke_test(uuid, exit=0):
    print 'running smoke test ...'
    agent = Agent(uuid)
    for T in range(0, 50):
        print 'test: %d' % T
        agent.testplugin.echo('have a nice day')
        admin = agent.Admin()
        print admin.hello()
        dog = agent.Dog()
        print dog.bark('RUF')
        print dog.bark('hello')
        print dog.wag(3)
        print dog.bark('hello again')
        rabbit = agent.Rabbit()
        print rabbit.hop(T)
        lion = agent.Lion()
        print lion.roar()
    print 'DONE'
    if exit:
        sys.exit(0)


def get_options():
    parser = OptionParser(option_class=ListOption)
    parser.add_option('-i', '--uuid', default='xyz', help='agent UUID')
    parser.add_option('-u', '--url', help='broker URL')
    parser.add_option('-t', '--threads', default=0, help='number of threads')
    parser.add_option('-U', '--user', action='extend', help='list of userid:password')
    parser.add_option('-T', '--transport', default='qpid', help='transport (qpid|amqplib)')
    parser.add_option('-a', '--auth', default='', help='enable message auth')
    opts, args = parser.parse_args()
    return opts


if __name__ == '__main__':
    options = get_options()
    uuid = options.uuid

    yp = {}
    for user in options.user:
        u, p = user.split(':')
        yp[u] = p

    url = options.url

    transport = options.transport or 'qpid'

    if options.auth:
        authenticator = TestAuthenticator()
    else:
        authenticator = None

    Agent.base_options['url'] = url
    Agent.base_options['transport'] = transport
    Agent.base_options['authenticator'] = authenticator

    queue = Queue(uuid.upper(), transport=transport)
    queue.declare(url)
    reply_consumer = ReplyConsumer(queue, url=url, transport=transport, authenticator=authenticator)
    reply_consumer.start(on_reply)

    # demo_progress(uuid, 1)
    # demo_window(uuid, 1)
    # test_performance(uuid)
    # demotest_performance(uuid)

    demo_getitem(uuid)
    demo_authentication(uuid, yp)
    demo_constructors(uuid)
    test_triggers(uuid)
    smoke_test(uuid)

    n_threads = int(options.threads)
    if n_threads:
        print '======= RUNNING %d THREADS ============' % n_threads
        sleep(2)
        last = threads(uuid, n_threads)
        last.join()
        sys.exit(0)
    for i in range(0, 100):
        print '======= %d ========' % i
        main(uuid)
    test_performance(uuid)
    print 'finished.'


