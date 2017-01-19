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
from datetime import datetime as dt

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

    url = None
    address = None
    base_options = {}

    def __new__(cls, *args, **options):
        all_options = dict(Agent.base_options)
        all_options.update(options)
        return RealAgent(url, address, **all_options)


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


def threads(n=10):
    t = None
    for i in range(0, n):
        name = 'Test%d' % i
        t = Thread(name=name, target=main)
        t.setDaemon(True)
        t.start()
        print 'thread: %s, started' % t.getName()
    return t


def test_performance():
    N = 200
    agent = Agent()
    dog = agent.Dog()
    t = Timer()
    t.start()
    print 'measuring performance ...'
    for i in range(0, N):
        dog.bark('performance!')
    t.stop()
    print 'total=%s, percall=%f (ms)' % (t, (t.duration()/N)*1000)
    # sys.exit(0)
    # ASYNCHRONOUS
    agent = Agent(wait=0)
    dog = agent.Dog()
    t = Timer()
    t.start()
    print 'measuring (async) performance ...'
    for i in range(0, N):
        dog.bark('performance!')
    t.stop()
    print 'total=%s, percall=%f (ms)' % (t, (t.duration()/N)*1000)
    sys.exit(0)


def test_memory():
    N = 10000
    with open(__file__) as fp:
        content = fp.read()
    agent = Agent(data=content)
    dog = agent.Dog()
    t = Timer()
    t.start()
    print 'testing memory ...'
    for n in range(0, N):
        dog.bark('hello!')
        print 'tested %d' % n
    t.stop()
    print 'total=%s, percall=%f (ms)' % (t, (t.duration()/N)*1000)
    sys.exit(0)


def test_zombie():
    agent = Agent()
    zombie = agent.Zombie()
    zombie.sleep(240)
    sys.exit(0)


def test_triggers():
    agent = Agent(trigger=1)
    dog = agent.Dog()
    t = dog.bark('delayed!')
    print t
    t()
    print 'Manual trigger, OK'
    

def demo_pam_authentication(yp, exit=0):
    # basic success
    agent = Agent(user='jortel', password=yp['jortel'])
    dog = agent.Dog()
    print dog.testpam()
    # @user synonym
    agent = Agent(user='jortel', password=yp['jortel'])
    dog = agent.Dog()
    print dog.testpam2()
    # the @pam with specified service
    agent = Agent(user='jortel', password=yp['jortel'])
    dog = agent.Dog()
    print dog.testpam3()
    # no user
    agent = Agent()
    try:
        dog = agent.Dog()
        dog.testpam()
        raise Exception('Exception (UserRequired) expected')
    except UserRequired:
        print 'no user, OK'
    # no password
    agent = Agent(user='jortel')
    try:
        dog = agent.Dog()
        dog.testpam()
        raise Exception('Exception (PasswordRequired) expected')
    except PasswordRequired:
        print 'no password, OK'
    # wrong user
    agent = Agent(user='xx', password='xx')
    try:
        dog = agent.Dog()
        dog.testpam()
        raise Exception('Exception (UserNotAuthorized) expected')
    except UserNotAuthorized:
        print 'wrong user, OK'
    # PAM failed
    agent = Agent(user='jortel', password='xx')
    try:
        dog = agent.Dog()
        dog.testpam()
        raise Exception('Exception (NotAuthenticated) expected')
    except NotAuthenticated:
        print 'PAM not authenticated, OK'
    # PAM failed, invalid service
    agent = Agent(user='jortel', password='xx')
    try:
        dog = agent.Dog()
        dog.testpam4()
        raise Exception('Exception (NotAuthenticated) expected')
    except NotAuthenticated:
        print 'PAM not authenticated, invalid service, OK'
    if exit:
        sys.exit(0)


def demo_layered_security(yp, exit=0):
    user = 'jortel'
    # multi-user
    for user in ('jortel', 'jortel'):
        agent = Agent(user=user, password=yp[user])
        dog = agent.Dog()
        print dog.testLayered()
    # mixed user and secret
    agent = Agent(user=user, password=yp[user], secret='elmer')
    dog = agent.Dog()
    print dog.testLayered2()
    dog = agent.Dog()
    print dog.testLayered2()
    try:
        agent = Agent()
        dog = agent.Dog()
        print dog.testLayered2()
        raise Exception('Exception (UserRequired) expected')
    except UserRequired:
        pass
    if exit:
        sys.exit(0)

        
def demo_shared_secret(exit=0):
    # success
    agent = Agent(secret='garfield')
    cat = agent.Cat()
    print cat.meow('secret, OK')
    # no secret
    agent = Agent()
    try:
        cat = agent.Cat()
        cat.meow('secret, OK')
        raise Exception('Exception (SecretRequired) expected')
    except SecretRequired:
        print 'secret required, OK'
    # wrong secret
    agent = Agent(secret='foo')
    try:
        cat = agent.Cat()
        cat.meow('secret, OK')
        raise Exception('Exception (SecretNotMatched) expected')
    except SecretNotMatched:
        print 'secret not matched, OK'
    if exit:
        sys.exit(0)
        

def demo_authentication(yp, exit=0):
    demo_shared_secret()
    demo_pam_authentication(yp)
    demo_layered_security(yp)
    if exit:
        sys.exit(0)


def demo_constructors(exit=0):
    agent = Agent()
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
        
        
def demo_getitem(exit=0):
    agent = Agent()
    fn = agent['Dog']['bark']
    print fn('RUF')
    if exit:
        sys.exit(0)
        

def demo_progress(exit=0):
    # synchronous
    def fn(report):
        pct = (float(report['completed'])/float(report['total']))*100
        print 'Progress: sn=%s, data=%s, total=%s, complete=%s, pct:%d%% details=%s' % \
            (report['sn'],
             report['data'],
             report['total'],
             report['completed'],
             int(pct),
             report['details'])
    agent = Agent(progress=fn, data={4: 5})
    p = agent.Progress()
    print p.send(4)
    if exit:
        sys.exit(0)
    

def main():
    address = Agent.address.split('/')[-1].upper()

    # test ttl (not expired)
    agent = Agent(ttl=3)
    dog = agent.Dog()
    print dog.sleep(1)

    # TTL
    agent = Agent(ttl=10)
    dog = agent.Dog()
    print dog.sleep(1)

    # synchronous
    print '(demo) synchronous'
    agent = Agent()
    demo(agent)

    # asynchronous (fire and forget)
    print '(demo) asynchronous fire-and-forget'
    agent = Agent(wait=0)
    demo(agent)

    # asynchronous
    print '(demo) asynchronous'
    agent = Agent(reply=address)
    demo(agent)


def smoke_test(exit=0):
    print 'running smoke test ...'
    agent = Agent()
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
        duck = agent.Duck()
        print duck.fly()
        print duck.quack('aflak')
        panther = agent.Panther()
        print panther.test_progress()
    print 'DONE'
    if exit:
        sys.exit(0)


def test_cancel(exit=0):
    agent = Agent(wait=0)
    cancel = agent.Cancel()
    sn = cancel.test()
    agent = Agent()
    admin = agent.Admin()
    canceled = admin.cancel(sn)
    print canceled
    if exit:
        sys.exit(0)


def test_forked(exit=0, with_cancel=1):
    agent = Agent()
    panther = agent.Panther()
    print 'forked test(): %s' % panther.test()
    print 'forked test_progress(): %s' % panther.test_progress()
    print 'forked test_suicide(): %s' % panther.test_suicide()
    try:
        panther.test_exceptions()
    except ValueError:
        pass
    if with_cancel:
        agent = Agent(wait=0)
        panther = agent.Panther()
        sn = panther.sleep(30)
        print 'started: %s' % sn
        sleep(3)
        admin = agent.Admin()
        print 'cancelled: {}'.format(admin.cancel(sn))
    if exit:
        sys.exit(0)


def test_plugin_shutdown(exit=0):
    agent = Agent()
    shutdown = agent.PluginShutdown()
    shutdown.request()
    if exit:
        sys.exit(0)


def get_options():
    parser = OptionParser(option_class=ListOption)
    parser.add_option('-r', '--address', default='xyz', help='address')
    parser.add_option('-u', '--url', help='broker URL')
    parser.add_option('-t', '--threads', default=0, help='number of threads')
    parser.add_option('-U', '--user', action='extend', help='list of userid:password')
    parser.add_option('-a', '--auth', default='', help='enable message auth')
    parser.add_option('-e', '--exchange', default='', help='exchange')
    opts, args = parser.parse_args()
    return opts


if __name__ == '__main__':
    options = get_options()

    url = options.url
    address = options.address

    yp = {}
    for user in options.user:
        u, p = user.split(':')
        yp[u] = p

    if options.auth:
        authenticator = TestAuthenticator()
    else:
        authenticator = None

    Agent.url = url
    Agent.address = address
    Agent.base_options['authenticator'] = authenticator

    # test_plugin_shutdown(1)
    # test_zombie()
    # test_memory()
    test_forked()

    queue = Queue(address.split('/')[-1].upper())
    queue.durable = False
    queue.declare(url)
    reply_consumer = ReplyConsumer(queue, url=url, authenticator=authenticator)
    reply_consumer.start(on_reply)

    # test_cancel()
    # demo_progress(1)
    # test_performance()

    demo_authentication(yp)
    smoke_test()
    demo_constructors()
    test_triggers()
    demo_getitem()

    n_threads = int(options.threads)
    if n_threads:
        print '======= RUNNING %d THREADS ============' % n_threads
        sleep(2)
        last = threads(n_threads)
        last.join()
        sys.exit(0)
    for i in range(0, 100):
        print '======= %d ========' % i
        main()

    test_performance()
    print 'finished.'


