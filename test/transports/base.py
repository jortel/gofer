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


from gofer.messaging.factory import Consumer

URL = 'amqp://localhost:5672'
N = 10


def producer_reader(package, queue):
    print 'using producer/reader'
    with package.Producer(url=URL) as p:
        for x in range(0, N):
            d = queue.destination()
            print '#%d - sent: %s' % (x, d.dict())
            p.send(d)
    received = 0
    with package.Reader(queue, url=URL) as r:
        while received < N:
            m, ack = r.next()
            if m is None:
                break
            ack()
            print '#%d - received: %s' % (received, m)
            received += 1
    print 'end'


def producer_consumer(package, queue):
    print 'using producer/consumer'

    class TestCon(Consumer):

        def __init__(self, queue):
            Consumer.__init__(self, queue, url=URL)
            self.reader = package.Reader(queue)
            self.received = 0

        def dispatch(self, envelope):
            self.received += 1
            print '%d/%d - %s' % (self.received, N, envelope)
            if self.received == N:
                self.stop()

    c = TestCon(queue)
    c.start()

    with package.Producer(url=URL) as p:
        for x in range(0, N):
            d = queue.destination()
            print '#%d - sent: %s' % (x, d.dict())
            p.send(d)

    c.join()
    print 'end'


def test_no_exchange(package):
    print 'test builtin (direct) exchange'
    queue = package.Queue('test_1')
    queue.durable = False
    queue.auto_delete = True
    queue.declare(URL)
    producer_reader(package, queue)


def test_direct_exchange(package):
    print 'test explicit (direct) exchange'
    exchange = package.Exchange.direct()
    queue = package.Queue('test_2', exchange=exchange)
    queue.durable = False
    queue.auto_delete = True
    queue.declare(URL)
    producer_reader(package, queue)


def test_custom_direct_exchange(package):
    print 'test custom (direct) exchange'
    exchange = package.Exchange('test_1.direct', 'direct')
    exchange.durable = False
    exchange.auto_delete = True
    exchange.declare(URL)
    queue = package.Queue('test_5', exchange=exchange)
    queue.durable = False
    queue.auto_delete = True
    queue.declare(URL)
    producer_reader(package, queue)


def test_topic_exchange(package):
    print 'test explicit (topic) exchange'
    exchange = package.Exchange.topic()
    queue = package.Queue('test_3', exchange=exchange, routing_key='#')
    queue.durable = False
    queue.auto_delete = True
    queue.declare(URL)
    producer_reader(package, queue)


def test_custom_topic_exchange(package):
    print 'test custom (topic) exchange'
    exchange = package.Exchange('test_2.topic', 'topic')
    exchange.durable = False
    exchange.auto_delete = True
    exchange.declare(URL)
    queue = package.Queue('test_6', exchange=exchange, routing_key='#')
    queue.durable = False
    queue.auto_delete = True
    queue.declare(URL)
    producer_reader(package, queue)


def test_consumer(package):
    print 'test consumer builtin (direct) exchange'
    queue = package.Queue('test_4')
    queue.durable = False
    queue.auto_delete = True
    queue.declare(URL)
    producer_consumer(package, queue)


def test(package):
    test_no_exchange(package)
    test_direct_exchange(package)
    test_custom_direct_exchange(package)
    test_topic_exchange(package)
    test_custom_topic_exchange(package)
    test_consumer(package)
    print 'DONE'