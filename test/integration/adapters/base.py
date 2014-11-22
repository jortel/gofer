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


from gofer.messaging.consumer import Consumer


N = 10


class Test(object):
    
    def __init__(self, url, adapter):
        self.url = url
        self.adapter = adapter

    def producer_reader(self, queue):
        print 'using producer/reader'
        with self.adapter.Producer(url=self.url) as p:
            for x in range(0, N):
                d = queue.destination(self.url)
                print '#%d - sent: %s' % (x, d.dict())
                p.send(d)
        received = 0
        with self.adapter.Reader(queue, url=self.url) as r:
            while received < N:
                m, ack = r.next()
                if m is None:
                    break
                ack()
                print '#%d - received: %s' % (received, m)
                received += 1
        print 'end'

    def producer_consumer(self, queue):
        print 'using producer/consumer'
    
        class TestCon(Consumer):
    
            def __init__(self, url, adapter):
                Consumer.__init__(self, queue, url=url)
                self.reader = adapter.Reader(queue, url=url)
                self.received = 0
    
            def dispatch(self, document):
                self.received += 1
                print '%d/%d - %s' % (self.received, N, document)
                if self.received == N:
                    self.stop()
    
        c = TestCon(self.url, self.adapter)
        c.start()
    
        with self.adapter.Producer(url=self.url) as p:
            for x in range(0, N):
                d = queue.destination(self.url)
                print '#%d - sent: %s' % (x, d.dict())
                p.send(d)
    
        c.join()
        print 'end'
    
    def test_no_exchange(self):
        print 'test builtin (direct) exchange'
        queue = self.adapter.Queue('test_1')
        queue.durable = False
        queue.auto_delete = True
        queue.declare(self.url)
        self.producer_reader(queue)

    def test_direct_exchange(self):
        print 'test explicit (direct) exchange'
        exchange = self.adapter.Exchange('amq.direct')
        queue = self.adapter.Queue('test_2', exchange=exchange)
        queue.durable = False
        queue.auto_delete = True
        queue.declare(self.url)
        self.producer_reader(queue)

    def test_custom_direct_exchange(self):
        print 'test custom (direct) exchange'
        exchange = self.adapter.Exchange('test_1.direct', 'direct')
        exchange.durable = False
        exchange.auto_delete = True
        exchange.declare(self.url)
        queue = self.adapter.Queue('test_5', exchange=exchange)
        queue.durable = False
        queue.auto_delete = True
        queue.declare(self.url)
        self.producer_reader(queue)
    
    def test_topic_exchange(self):
        print 'test explicit (topic) exchange'
        exchange = self.adapter.Exchange('amq.topic')
        queue = self.adapter.Queue('test_3', exchange=exchange, routing_key='#')
        queue.durable = False
        queue.auto_delete = True
        queue.declare(self.url)
        self.producer_reader(queue)

    def test_custom_topic_exchange(self):
        print 'test custom (topic) exchange'
        exchange = self.adapter.Exchange('test_2.topic', 'topic')
        exchange.durable = False
        exchange.auto_delete = True
        exchange.declare(self.url)
        queue = self.adapter.Queue('test_6', exchange=exchange, routing_key='#')
        queue.durable = False
        queue.auto_delete = True
        queue.declare(self.url)
        self.producer_reader(queue)

    def test_consumer(self):
        print 'test consumer builtin (direct) exchange'
        queue = self.adapter.Queue('test_4')
        queue.durable = False
        queue.auto_delete = True
        queue.declare(self.url)
        self.producer_consumer(queue)

    def __call__(self):
        self.test_no_exchange()
        self.test_direct_exchange()
        self.test_custom_direct_exchange()
        self.test_topic_exchange()
        self.test_custom_topic_exchange()
        self.test_consumer()
        print 'DONE'