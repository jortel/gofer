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
from gofer.messaging import Producer, Reader, Exchange, Queue


N = 10


class Test(object):

    def __init__(self, url):
        self.url = url

    def __call__(self):
        self.test_no_exchange()
        self.test_custom_direct_exchange()
        self.test_custom_topic_exchange()
        self.test_consumer()
        print 'DONE'

    def producer_reader(self, queue):
        print 'using producer/reader'
        with Producer(url=self.url) as p:
            for x in range(0, N):
                d = queue.destination(self.url)
                print '#%d - sent: %s' % (x, d.dict())
                p.send(d)
        received = 0
        with Reader(queue, url=self.url) as r:
            while received < N:
                m, d = r.next()
                if m is None:
                    break
                m.ack()
                print '#%d - received: %s' % (received, d)
                received += 1
        print 'end'

    def producer_consumer(self, queue):
        print 'using producer/consumer'

        class TestCon(Consumer):

            def __init__(self, url):
                Consumer.__init__(self, queue, url=url)
                self.received = 0

            def dispatch(self, document):
                self.received += 1
                print '%d/%d - %s' % (self.received, N, document)
                if self.received == N:
                    self.stop()

        c = TestCon(self.url)
        c.start()

        with Producer(url=self.url) as p:
            for x in range(0, N):
                d = queue.destination(self.url)
                print '#%d - sent: %s' % (x, d.dict())
                p.send(d)

        c.join()
        print 'end'

    def test_no_exchange(self):
        print 'test builtin (direct) exchange'
        queue = Queue('test_1')
        queue.durable = False
        queue.auto_delete = True
        queue.declare(self.url)
        self.producer_reader(queue)

    def test_custom_direct_exchange(self):
        print 'test custom (direct) exchange'
        exchange = Exchange('test_1.direct', policy='direct')
        exchange.durable = False
        exchange.auto_delete = True
        exchange.declare(self.url)
        queue = Queue('test_5', exchange=exchange)
        queue.durable = False
        queue.auto_delete = True
        queue.declare(self.url)
        self.producer_reader(queue)

    def test_custom_topic_exchange(self):
        print 'test custom (topic) exchange'
        exchange = Exchange('test_2.topic', policy='topic')
        exchange.durable = False
        exchange.auto_delete = True
        exchange.declare(self.url)
        queue = Queue('test_6', exchange=exchange, routing_key='#')
        queue.durable = False
        queue.auto_delete = True
        queue.declare(self.url)
        self.producer_reader(queue)

    def test_consumer(self):
        print 'test consumer builtin (direct) exchange'
        queue = Queue('test_4')
        queue.durable = False
        queue.auto_delete = True
        queue.declare(self.url)
        self.producer_consumer(queue)

