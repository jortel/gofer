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

from time import sleep
from optparse import OptionParser, Option
from hashlib import sha256
from logging import basicConfig
from threading import Thread

from gofer.rmi.window import *
from gofer.rmi.dispatcher import *
from gofer.rmi.async import ReplyConsumer
from gofer.metrics import Timer
from gofer.proxy import Agent as RealAgent
from gofer.messaging import Queue, Authenticator, ValidationFailed

from plugins import *

basicConfig(filename='/opt/gofer/server.log')

log = getLogger(__name__)

# getLogger('gofer.adapter').setLevel(DEBUG)
# getLogger('gofer.messaging').setLevel(DEBUG)


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


def threads(uuid, url, n=10):
    t = None
    for i in range(0, n):
        name = 'Test%d' % i
        t = Thread(name=name, target=main, args=(uuid, url))
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
    for i in range(0, N):
        dog.bark('performance!')
    t.stop()
    print 'total=%s, percall=%f (ms)' % (t, (t.duration()/N)*1000)
    #sys.exit(0)
    # ASYNCHRONOUS
    agent = Agent(uuid, wait=0)
    dog = agent.Dog()
    t = Timer()
    t.start()
    print 'measuring (async) performance ...'
    for i in range(0, N):
        dog.bark('performance!')
    t.stop()
    print 'total=%s, percall=%f (ms)' % (t, (t.duration()/N)*1000)
    sys.exit(0)


def test_triggers(uuid):
    agent = Agent(uuid, trigger=1)
    dog = agent.Dog()
    t = dog.bark('delayed!')
    print t
    t()
    print 'Manual trigger, OK'
    

def demo_window(uuid, exit=0):
    route = uuid.upper()
    print 'demo window, +10, +10min seconds'
    begin = later(seconds=10)
    window = Window(begin=begin, seconds=5)
    agent = Agent(uuid, reply=route)
    dog = agent.Dog(window=window, any='demo')
    print dt.now()
    print dog.bark('hello, after 10 seconds')
    print dog.wag(3)
    print dog.bark('hello again, after 10 seconds')
    sleep(120)
    if exit:
        sys.exit(0)
    

def demo_pam_authentication(uuid, yp, exit=0):
    # basic success
    agent = Agent(uuid, user='jortel', password=yp['jortel'])
    dog = agent.Dog()
    print dog.testpam()
    # @user synonym
    agent = Agent(uuid, user='root', password=yp['root'])
    dog = agent.Dog()
    print dog.testpam2()
    # the @pam with specified service
    agent = Agent(uuid, user='jortel', password=yp['jortel'])
    dog = agent.Dog()
    print dog.testpam3()
    # no user
    agent = Agent(uuid)
    try:
        dog = agent.Dog()
        dog.testpam()
        raise Exception('Exception (UserRequired) expected')
    except UserRequired:
        print 'no user, OK'
    # no password
    agent = Agent(uuid, user='jortel')
    try:
        dog = agent.Dog()
        dog.testpam()
        raise Exception('Exception (PasswordRequired) expected')
    except PasswordRequired:
        print 'no password, OK'
    # wrong user
    agent = Agent(uuid, user='xx', password='xx')
    try:
        dog = agent.Dog()
        dog.testpam()
        raise Exception('Exception (UserNotAuthorized) expected')
    except UserNotAuthorized:
        print 'wrong user, OK'
    # PAM failed
    agent = Agent(uuid, user='jortel', password='xx')
    try:
        dog = agent.Dog()
        dog.testpam()
        raise Exception('Exception (NotAuthenticated) expected')
    except NotAuthenticated:
        print 'PAM not authenticated, OK'
    # PAM failed, invalid service
    agent = Agent(uuid, user='jortel', password='xx')
    try:
        dog = agent.Dog()
        dog.testpam4()
        raise Exception('Exception (NotAuthenticated) expected')
    except NotAuthenticated:
        print 'PAM not authenticated, invalid service, OK'
    if exit:
        sys.exit(0)


def demo_layered_security(uuid, yp, exit=0):
    user = 'jortel'
    # multi-user
    for user in ('jortel', 'root'):
        agent = Agent(uuid, user=user, password=yp[user])
        dog = agent.Dog()
        print dog.testLayered()
    # mixed user and secret
    agent = Agent(uuid, user=user, password=yp[user], secret='elmer')
    dog = agent.Dog()
    print dog.testLayered2()
    dog = agent.Dog()
    print dog.testLayered2()
    try:
        agent = Agent(uuid)
        dog = agent.Dog()
        print dog.testLayered2()
        raise Exception('Exception (UserRequired) expected')
    except UserRequired:
        pass
    if exit:
        sys.exit(0)

        
def demo_shared_secret(uuid, exit=0):
    # success
    agent = Agent(uuid, secret='garfield')
    cat = agent.Cat()
    print cat.meow('secret, OK')
    # no secret
    agent = Agent(uuid)
    try:
        cat = agent.Cat()
        cat.meow('secret, OK')
        raise Exception('Exception (SecretRequired) expected')
    except SecretRequired:
        print 'secret required, OK'
    # wrong secret
    agent = Agent(uuid, secret='foo')
    try:
        cat = agent.Cat()
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
    for name, age in (('jeff', 10), ('bart', 45),):
        cowboy = agent.Cowboy(name, age=age)
        print cowboy.howdy()
        assert(cowboy.name() == name)
        assert(cowboy.age() == age)
    try:
        cowboy = agent.Cowboy()
        print cowboy.howdy()
        raise Exception('Cowboy() should have failed.')
    except TypeError:
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
    agent = Agent(uuid, progress=fn, any={4: 5})
    p = agent.Progress()
    print p.send(4)
    if exit:
        sys.exit(0)
    

def main(uuid, url):
    route = uuid.upper()

    # test timeout (not expired)
    agent = Agent(uuid, timeout=3)
    dog = agent.Dog()
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
    agent = Agent(uuid, reply=route, window=window)
    demo(agent)

    # group 2
    print 'group 2'
    begin = later(seconds=20)
    window = Window(begin=begin, minutes=10)
    agent = Agent(uuid, reply=route, window=window, any='group 2')
    dog = agent.Dog()
    print dog.bark('hello')
    print dog.wag(3)
    print dog.bark('hello again')

    # group 1
    print 'group 1'
    begin = later(seconds=10)
    window = Window(begin=begin, minutes=10)
    agent = Agent(uuid, reply=route, window=window, any='group 1')
    dog = agent.Dog()
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
    parser.add_option('-a', '--auth', default='', help='enable message auth')
    parser.add_option('-e', '--exchange', default='', help='exchange')
    opts, args = parser.parse_args()
    return opts


if __name__ == '__main__':
    options = get_options()
    uuid = options.uuid
    exchange = options.exchange

    if exchange:
        route = '/'.join((exchange, uuid))
    else:
        route = None

    yp = {}
    for user in options.user:
        u, p = user.split(':')
        yp[u] = p

    url = options.url

    if options.auth:
        authenticator = TestAuthenticator()
    else:
        authenticator = None

    Agent.base_options['url'] = url
    Agent.base_options['authenticator'] = authenticator
    Agent.base_options['route'] = route

    queue = Queue(uuid.upper())
    queue.durable = False
    queue.declare(url)
    reply_consumer = ReplyConsumer(queue, url=url, authenticator=authenticator)
    reply_consumer.start(on_reply)

    # demo_progress(uuid, 1)
    # demo_window(uuid, 1)
    # test_performance(uuid)

    demo_authentication(uuid, yp)
    smoke_test(uuid)
    demo_constructors(uuid)
    test_triggers(uuid)
    demo_getitem(uuid)

    n_threads = int(options.threads)
    if n_threads:
        print '======= RUNNING %d THREADS ============' % n_threads
        sleep(2)
        last = threads(uuid, url, n_threads)
        last.join()
        sys.exit(0)
    for i in range(0, 100):
        print '======= %d ========' % i
        main(uuid, url)

    test_performance(uuid)
    print 'finished.'


