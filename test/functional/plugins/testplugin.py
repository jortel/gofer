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
from hashlib import sha256
from logging import getLogger

from gofer.decorators import *
from gofer.agent.plugin import Plugin
from gofer.agent.rmi import Context
from gofer.messaging import Producer, Exchange, Destination
from gofer.messaging.auth import Authenticator, ValidationFailed

log = getLogger(__name__)
plugin = Plugin.find(__name__)
builtin = Plugin.find('builtin')
cfg = plugin.cfg()

HEARTBEAT = 500

plugin += builtin
plugin += builtin['Rabbit']

# whiteboard
plugin.whiteboard['secret'] = 'garfield'


@initializer
def init_plugin():
    print 'Initialized!'


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

if cfg.messaging.auth:
    plugin.authenticator = TestAuthenticator()


class BadException(Exception):
    def __init__(self):
        self.cat = Cat()


class MyError(Exception):
    def __init__(self, a, b):
        Exception.__init__(self, a)
        self.b = b


class RepoLib:
    @remote
    def update(self):
        print 'Repo updated'


class Cat:
    
    @remote(secret=plugin.whiteboard['secret'])
    def meow(self, words):
        print 'Ruf %s' % words
        return 'Yes master.  I will meow because that is what cats do. "%s"' % words
    
    @remote
    def returnObject(self):
        return self
    
    @remote
    def badException(self):
        raise BadException()
    
    @remote
    def superMethod(self, a, *names, **opts):
        pass


class Dog:
    
    def __init__(self, name='chance'):
        self.name = name
    
    @remote
    def bark(self, words, wait=0):
        if wait:
            sleep(wait)
        print '[%s] Ruf %s' % (self.name, words)
        return 'Yes master.  I will bark because that is what dogs do. "%s"' % words

    @remote
    def wag(self, n):
        for i in range(0, n):
            print 'wag'
        return 'Yes master.  I will wag my tail because that is what dogs do.'
    
    @remote
    def keyError(self, key):
        raise KeyError, key
    
    @remote
    def myError(self):
        raise MyError('This is myerror.', 23)
    
    @remote
    def sleep(self, n):
        sleep(n)
        return 'Good morning, master!'

    def notpermitted(self):
        print 'not permitted.'
        
    @remote
    @pam(user='jortel')
    def testpam(self):
        return 'PAM is happy!'
    
    @remote
    @user(name='root')
    def testpam2(self):
        return 'PAM (2) is happy!'
    
    @remote
    @pam(user='jortel', service='su')
    def testpam3(self):
        return 'PAM (3) is happy!'
    
    @remote
    @pam(user='jortel', service='xx')
    def testpam4(self):
        return 'PAM (4) is happy!'
    
    
    @user(name='root')
    @user(name='jortel')
    @remote(secret='elmer')
    def testLayered(self):
        return 'LAYERED (1) is happy'

    @user(name='root')
    @remote(secret='elmer')
    def testLayered2(self):
        return 'LAYERED (2) is happy'
    
    @remote
    def __str__(self):
        return 'REMOTE:Dog'


class Cowboy:
    
    def __init__(self, name, age=0):
        self.__name = name
        self.__age = age
    
    @remote
    def howdy(self):
        n = self.name()
        a = self.age()
        return 'Howdy, name=%s; age=%d' % (n, a)
    
    @remote
    def name(self):
        return self.__name
    
    @remote
    def age(self):
        return self.__age
    

class Cancel:
    """
    Test cancel
    """

    @remote
    def test(self):
        ctx = Context.current()
        for n in range(0,100):
            log.info(ctx.sn)
            sleep(1)
            if ctx.cancelled():
                return 'cancelled'
        return 'finished'


class Progress:
    """
    Test progress reporting
    """
    
    @remote
    def send(self, total):
        ctx = Context.current()
        ctx.progress.total = total
        for n in range(0, total):
            ctx.progress.completed += 1
            ctx.progress.details = 'for: %d' % n
            ctx.progress.report()
            sleep(1)
        return 'sent, boss'
    
    @remote
    def send_half(self, total):
        ctx = Context.current()
        ctx.progress.total = total
        for n in range(0, total):
            if n < (total/2):
                ctx.progress.completed += 1
                ctx.progress.report()
            sleep(1)
        return 'sent, boss'


@action(minutes=5)
def testAction():
    log.info('Testing')


class Heartbeat:
    """
    Provide agent heartbeat.
    """

    @action(seconds=HEARTBEAT)
    def heartbeat(self):
        return self.send()

    @remote
    def send(self):
        delay = int(HEARTBEAT)
        url = plugin.get_url()
        transport = plugin.get_transport()
        topic = Exchange.topic(transport=transport)
        destination = Destination('heartbeat', exchange=topic.name)
        myid = plugin.getuuid()
        if myid:
            with Producer(url=url, transport=transport) as p:
                body = dict(uuid=myid, next=delay)
                p.send(destination, ttl=delay, heartbeat=body)
        return myid
