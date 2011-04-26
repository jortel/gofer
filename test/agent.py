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

import sys
from time import sleep
from gofer.messaging import Queue
from gofer.messaging.base import Agent as Base
from gofer.messaging.decorators import *
from gofer.messaging.consumer import RequestConsumer
from gofer.messaging.broker import Broker
from logging import INFO, basicConfig

basicConfig(filename='/tmp/gofer/agent.log', level=INFO)

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


class Dog:
    @remote
    def bark(self, words):
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


class Agent(Base):
    def __init__(self, id, threads):
        queue = Queue(id)
        #url = 'ssl://localhost:5674'
        url = 'tcp://localhost:5672'
        broker = Broker(url)
        broker.cacert = '/etc/pki/qpid/ca/ca.crt'
        broker.clientcert = '/etc/pki/qpid/client/client.pem'
        Base.__init__(
            self,
            RequestConsumer(queue, url=url),
            threads)
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
    print 'starting agent (%s), threads=%d' % (uuid, threads)
    agent = Agent(uuid, threads)
