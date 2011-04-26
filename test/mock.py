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

from time import sleep
from gofer.messaging import mock
from gofer.messaging.dispatcher import NotPermitted

mock.install()

from server import main
from gofer import proxy


class MyError(Exception):
    def __init__(self, a, b):
        Exception.__init__(self, a)
        self.b = b

class Admin:

    def hello(self):
        s = []
        s.append('[mock]: Hello, I am gofer agent.')
        s.append('Status: ready')
        return '\n'.join(s)

class RepoLib:

    def update(self):
        print '[mock]: Repo updated'
        
class Cat:

    def meow(self, words):
        print '[mock]: Ruf %s' % words
        return '[mock]: Yes master.  I will meow because that is what cats do. "%s"' % words


class Dog:

    def bark(self, words):
        print '[mock]:  Ruf %s' % words
        return '[mock]: Yes master.  I will bark because that is what dogs do. "%s"' % words

    def wag(self, n):
        for i in range(0, n):
            print '[mock]:  wag'
        return '[mock]: Yes master.  I will wag my tail because that is what dogs do.'

    def keyError(self, key):
        raise KeyError, key

    def myError(self):
        raise MyError('[mock]: This is myerror.', 23)

    def sleep(self, n):
        sleep(n)
        return '[mock]: Good morning, master!'

    def notpermitted(self):
        print '[mock]: not permitted.'
        raise NotPermitted(('Dog','notpermitted'))

class Main:

    def echo(self, x):
        return x

    
mock.register(__main__=Main(),
              Admin=Admin,
              Dog=Dog,
              Cat=Cat,
              RepoLib=RepoLib(),)

def test():
    a = proxy.agent('123')
    dogA = a.Dog()
    dogA.bark('hello')
    dogA.wag(2)
    print 'calls for dogA.bark()'
    for call in dogA.bark.history():
        print call
    print 'calls for dogA.wag()'
    for call in dogA.wag.history():
        print call
    b = proxy.agent('123b')
    dogB = b.Dog()
    dogB.bark('foo')
    dogB.bark('bar')
    print 'calls for dogB.bark()'
    for call in dogB.bark.history():
        print call
    print 'reset B'
    mock.reset()
    b = proxy.agent('123b')
    dogB = b.Dog()
    print 'calls for dogB'
    for call in dogB.bark.history():
        print call

if __name__ == '__main__':
    test()
    uuid = 'xyz'
    main(uuid)
    agent = proxy.agent(uuid)
    d = agent.Dog()
    for x in d.bark.history():
        print x
    print 'finished.'


