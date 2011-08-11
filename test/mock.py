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
from gofer.rmi import mock
from gofer.rmi.dispatcher import NotPermitted

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


