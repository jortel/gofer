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
from time import sleep
from gofer.agent.config import Config, nvl
Config.PATH = '/tmp/gofer/agent.conf'
Config.CNFD = '/tmp/gofer/conf.d'
from gofer.messaging import Queue
from gofer.decorators import *
from gofer.rmi.consumer import RequestConsumer
from gofer.messaging.broker import Broker
from gofer.agent.plugin import PluginDescriptor, PluginLoader
from gofer.agent.main import Agent, eager
from logging import getLogger, INFO, DEBUG

log = getLogger(__name__)

DESCRIPTOR = \
"""
[main]
enabled=1

[messaging]
uuid=%s
threads=%s
"""

class BadException(Exception):
    def __init__(self):
        self.cat = Cat()

class MyError(Exception):
    def __init__(self, a, b):
        Exception.__init__(self, a)
        self.b = b

class Admin:

    @remote
    def hello(self):
        s = []
        s.append('Hello, I am gofer agent.')
        s.append('Status: ready')
        return '\n'.join(s)

class RepoLib:
    @remote
    def update(self):
        print 'Repo updated'
        
class Cat:
    
    @remote(secret='garfield')
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
    @remote
    def bark(self, words, wait=0):
        if wait:
            sleep(wait)
        print 'Ruf %s' % words
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
    
    @remote
    def __str__(self):
        return 'REMOTE:Dog'
        
        
@remote
def echo(s):
    return s

@action(minutes=5)
def testAction():
    log.info('Testing')


def install(uuid, threads=1):
    descriptor = DESCRIPTOR % (uuid, threads)
    PluginDescriptor.ROOT = '/tmp/gofer/plugins'
    PluginLoader.PATH = ['/tmp/gofer/lib/plugins']
    for path in (PluginDescriptor.ROOT, PluginLoader.PATH[0]):
        if not os.path.exists(path):
            os.makedirs(path)
    path = os.path.join(PluginDescriptor.ROOT, 'agent.conf')
    f = open(path, 'w')
    f.write(descriptor)
    f.close()
    f = open(__file__)
    s = f.read()
    f.close()
    path = os.path.join(PluginLoader.PATH[0], 'agent.py')
    f = open(path, 'w')
    f.write(s)
    f.close()
    

class TestAgent:
    def __init__(self, id, threads):
        install(id, threads)
        queue = Queue(id)
        url = 'ssl://localhost:5674'
        url = 'tcp://50.17.201.180:5672'
        url = 'tcp://localhost:5672'
        broker = Broker(url)
        broker.cacert = '/etc/pki/qpid/ca/ca.crt'
        broker.clientcert = '/etc/pki/qpid/client/client.pem'
        rq = RequestConsumer(queue, url=url)
        rq.start()
        pl = PluginLoader()
        plugins = pl.load(eager())
        agent = Agent(plugins)
        agent.start(False)
        while True:
            sleep(10)
            print 'Agent: sleeping...'

if __name__ == '__main__':
    uuid = 'xyz'
    threads = 1
    if len(sys.argv) > 1:
        threads = int(sys.argv[1])
    if len(sys.argv) > 2:
        uuid = sys.argv[2]
    log.info('started')
    print 'starting agent (%s), threads=%d' % (uuid, threads)
    agent = TestAgent(uuid, threads)
