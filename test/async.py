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
sys.path.append('../../')

from time import sleep
from gofer.messaging import Queue
from gofer.messaging.async import ReplyConsumer
from logging import INFO, basicConfig

basicConfig(filename='/tmp/messaging.log', level=INFO)


def callback(reply):
    print 'CB:\n%s' % reply


class Listener:

    def succeeded(self, reply):
        print reply

    def failed(self, reply):
        print reply

    def status(self, reply):
        print reply


if __name__ == '__main__':
    tag = 'XYZ'
    print 'starting, uuid=%s' % tag
    c = ReplyConsumer(Queue(tag))
    #c.start(Listener())
    c.start(callback)
    while True:
        #print 'ReplyListener: sleeping...'
        sleep(10)
    c.stop()
