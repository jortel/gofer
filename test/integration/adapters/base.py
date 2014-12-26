# Copyright (c) 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

N = 10

from gofer.messaging import Queue, Destination


class Test(object):
    
    def __init__(self, url, adapter):
        self.url = url
        self.adapter = adapter

    def producer_reader(self, destination):
        print 'using producer/reader'
        with self.adapter.Sender(url=self.url) as p:
            for x in range(0, N):
                print '#%d - sent: %s' % (x, destination.dict())
                p.send(destination, 'hello')
        received = 0
        queue = Queue(destination.routing_key)
        with self.adapter.Reader(queue, url=self.url) as r:
            while received < N:
                m = r.get(1)
                if m is None:
                    break
                m.ack()
                print '#%d - received: %s' % (received, m)
                received += 1
        assert received == N
        print 'end'
    
    def test_no_exchange(self):
        print 'test builtin (direct) exchange'
        queue = self.adapter.Queue('test_1')
        queue.durable = False
        queue.auto_delete = True
        queue.declare(self.url)
        destination = Destination(queue.name)
        self.producer_reader(destination)

    def test_direct_exchange(self):
        print 'test explicit (direct) exchange'
        exchange = self.adapter.Exchange('amq.direct')
        queue = self.adapter.Queue('test_2')
        queue.durable = False
        queue.auto_delete = True
        queue.declare(self.url)
        exchange.bind(queue, self.url)
        destination = Destination(queue.name, exchange.name)
        self.producer_reader(destination)

    def test_custom_direct_exchange(self):
        print 'test custom (direct) exchange'
        exchange = self.adapter.Exchange('test_1.direct', 'direct')
        exchange.durable = False
        exchange.auto_delete = True
        exchange.declare(self.url)
        queue = self.adapter.Queue('test_5')
        queue.durable = False
        queue.auto_delete = True
        queue.declare(self.url)
        exchange.bind(queue, self.url)
        destination = Destination(queue.name, exchange.name)
        self.producer_reader(destination)
    
    def test_topic_exchange(self):
        print 'test explicit (topic) exchange'
        exchange = self.adapter.Exchange('amq.topic')
        queue = self.adapter.Queue('test_3')
        queue.durable = False
        queue.auto_delete = True
        queue.declare(self.url)
        exchange.bind(queue, self.url)
        destination = Destination(queue.name, exchange.name)
        self.producer_reader(destination)

    def test_custom_topic_exchange(self):
        print 'test custom (topic) exchange'
        exchange = self.adapter.Exchange('test_2.topic', 'topic')
        exchange.durable = False
        exchange.auto_delete = True
        exchange.declare(self.url)
        queue = self.adapter.Queue('test_6')
        queue.durable = False
        queue.auto_delete = True
        queue.declare(self.url)
        exchange.bind(queue, self.url)
        destination = Destination(queue.name, exchange.name)
        self.producer_reader(destination)

    def __call__(self):
        self.test_no_exchange()
        self.test_direct_exchange()
        self.test_custom_direct_exchange()
        self.test_topic_exchange()
        self.test_custom_topic_exchange()
        print 'DONE'