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
from gofer.messaging import Queue
from gofer.messaging.base import Container
from gofer.messaging.producer import Producer
from gofer.messaging.window import *
from gofer.proxy import Agent
from time import sleep
from datetime import datetime as dt
from datetime import timedelta as delta
from logging import INFO, basicConfig, getLogger
from agent import MyError

basicConfig(filename='/tmp/gofer/server.log', level=INFO)

log = getLogger(__name__)


def demo(agent):

    agent.__main__.echo('have a nice day')
    
    admin = agent.Admin()
    
    print admin.hello()
    
    dog = agent.Dog()
    repolib = agent.RepoLib()
    print dog.bark('RUF')
    print dog.bark('hello')
    print dog.wag(3)
    print dog.bark('hello again')
    print repolib.update()
    try:
        print repolib.updated()
    except Exception, e:
        log.info('failed:', exc_info=True)
        print e
    try:
        print dog.notpermitted()
    except Exception, e:
        log.info('failed:', exc_info=True)
        print e
    try:
        print plugin.notdecorated()
    except Exception, e:
        log.info('failed:', exc_info=True)
        print e
    try:
        print dog.keyError('jeff')
    except KeyError, e:
        log.info('failed:', exc_info=True)
        print e
    except Exception, e:
        log.info('failed:', exc_info=True)
        print e
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

def main():
    uuid = 'xyz'

    # TTL
    agent = Agent(uuid, timeout=10)
    dog = agent.Dog()
    print dog.sleep(1)
    
    # synchronous
    print '(demo) synchronous'
    agent = Agent(uuid)
    demo(agent)
    #agent.delete()
    agent = None

    # asynchronous (fire and forget)
    print '(demo) asynchronous fire-and-forget'
    agent = Agent(uuid, async=True)
    demo(agent)

    # asynchronous
    print '(demo) asynchronous'
    tag = 'xyz'
    window = Window(begin=dt.utcnow(), minutes=1)
    agent = Agent(uuid, ctag=tag, window=window)
    demo(agent)

    # asynchronous
    print '(demo) group asynchronous'
    tag = 'xyz'
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
    opts = dict(window=window, any='group 2')
    print dog.bark('hello', **opts)
    print dog.wag(3, **opts)
    print dog.bark('hello again', **opts)

    # group 1

    print 'group 1'
    begin = later(seconds=10)
    window = Window(begin=begin, minutes=10)
    opts = dict(window=window, any='group 1')
    print dog.bark('hello', **opts)
    print dog.wag(3, **opts)
    print dog.bark('hello again', **opts)

    agent = None

if __name__ == '__main__':
    for i in range(0,10):
        print '======= %d ========' % i
        main()
    print 'finished.'


