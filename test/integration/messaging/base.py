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


class Route(object):

    def __init__(self, route):
        self.route = route
        self.parts = route.split('/')

    @property
    def exchange(self):
        if len(self.parts) > 1:
            return self.parts[0]
        else:
            return ''

    @property
    def queue(self):
        return self.parts[-1]

    def __str__(self):
        return self.route


class Test(object):

    def __init__(self, url):
        self.url = url

    def producer_reader(self, route):
        print 'using producer/reader'
        with Producer(url=self.url) as p:
            for x in range(0, N):
                print '#%d - sent: %s' % (x, route)
                p.send(str(route))
        received = 0
        queue = Queue(route.queue)
        with Reader(queue, url=self.url) as r:
            while received < N:
                m, d = r.next()
                if m is None:
                    break
                m.ack()
                print '#%d - received: %s' % (received, d)
                received += 1
        print 'end'

    def producer_consumer(self, route):
        print 'using producer/consumer'

        class TestCon(Consumer):

            def __init__(self, url):
                queue = Queue(route.queue)
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
                print '#%d - sent: %s' % (x, route)
                p.send(str(route))

        c.join()
        print 'end'

    def test_no_exchange(self):
        print 'test builtin (direct) exchange'
        route = Route('test_10')
        queue = Queue(route.queue)
        queue.durable = False
        queue.auto_delete = True
        queue.declare(self.url)
        self.producer_reader(route)

    def test_custom_direct_exchange(self):
        print 'test custom (direct) exchange'
        route = Route('test_11.direct/test_11')
        exchange = Exchange(route.exchange, policy='direct')
        exchange.durable = False
        exchange.auto_delete = True
        exchange.declare(self.url)
        queue = Queue(route.queue)
        queue.durable = False
        queue.auto_delete = True
        queue.declare(self.url)
        exchange.bind(queue, self.url)
        self.producer_reader(route)

    def test_custom_topic_exchange(self):
        print 'test custom (topic) exchange'
        route = Route('test_12.topic/test_12')
        exchange = Exchange(route.exchange, policy='topic')
        exchange.durable = False
        exchange.auto_delete = True
        exchange.declare(self.url)
        queue = Queue(route.queue)
        queue.durable = False
        queue.auto_delete = True
        queue.declare(self.url)
        exchange.bind(queue, self.url)
        self.producer_reader(route)

    def test_crud(self):
        print 'test CRUD'
        queue = Queue('test_crud_13')
        queue.durable = False
        queue.declare(self.url)
        exchange = Exchange('test_crud_13.direct')
        exchange.declare(self.url)
        exchange.bind(queue, self.url)
        queue.delete(self.url)
        exchange.delete(self.url)

    def __call__(self):
        self.test_crud()
        self.test_no_exchange()
        self.test_custom_direct_exchange()
        self.test_custom_topic_exchange()
        print 'DONE'

