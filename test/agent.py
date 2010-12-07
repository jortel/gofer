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

basicConfig(filename='/tmp/gofer.log', level=INFO)

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

    def notpermitted(self):
        print 'not permitted.'
        

@remote
def echo(something):
    print something
    return something


def notdecorated():
    pass
        

class Agent(Base):
    def __init__(self, id):
        queue = Queue(id)
        #url = 'ssl://localhost:5674'
        url = 'tcp://localhost:5672'
        broker = Broker.get(url)
        broker.cacert = '/etc/pki/qpid/ca/ca.crt'
        broker.clientcert = '/etc/pki/qpid/client/client.pem'
        Base.__init__(self, RequestConsumer(queue, url=url))
        while True:
            sleep(10)
            print 'Agent: sleeping...'

if __name__ == '__main__':
    uuid = 'xyz'
    if len(sys.argv) > 1:
        uuid = sys.argv[1]
    print 'starting agent (%s)' % uuid
    agent = Agent(uuid)
