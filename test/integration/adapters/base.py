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

from uuid import uuid4

from gofer.messaging import Queue, NotFound

N = 10


class Address(object):

    def __init__(self, address):
        self.address = address
        self.parts = address.split('/')

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
        return self.address


class Test(object):
    
    def __init__(self, url, adapter):
        self.url = url
        self.adapter = adapter

    def producer_reader(self, address):
        print 'using producer/reader'
        with self.adapter.Sender(url=self.url) as p:
            for x in range(0, N):
                print '#%d - sent: %s' % (x, address)
                p.send(str(address), 'hello')
        received = 0
        queue = Queue(address.queue)
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

    def test_not_found(self):
        print 'test not-found'
        address = Address(str(uuid4()))
        sender = None
        reader = None
        # sender
        try:
            sender = self.adapter.Sender(self.url)
            sender.open()
            sender.send(str(address), 'hello')
            raise Exception('NotFound not raised.')
        except NotFound:
            pass
        finally:
            sender.close()
        # reader
        try:
            queue = self.adapter.Queue(address.queue)
            reader = self.adapter.Reader(queue, self.url)
            reader.open()
            reader.get()
            raise Exception('NotFound not raised.')
        except NotFound:
            pass
        finally:
            reader.close()
    
    def test_no_exchange(self):
        print 'test builtin (direct) exchange'
        address = Address('test.1')
        queue = self.adapter.Queue(address.queue)
        queue.durable = False
        queue.declare(self.url)
        self.producer_reader(address)

    def test_direct_exchange(self):
        print 'test explicit (direct) exchange'
        address = Address('amq.direct/test.2')
        exchange = self.adapter.Exchange(address.exchange, 'direct')
        queue = self.adapter.Queue(address.queue)
        queue.durable = False
        queue.declare(self.url)
        exchange.bind(queue, self.url)
        self.producer_reader(address)

    def test_custom_direct_exchange(self):
        print 'test custom (direct) exchange'
        address = Address('test_3.direct/test.3')
        exchange = self.adapter.Exchange(address.exchange, 'direct')
        exchange.durable = False
        exchange.auto_delete = True
        exchange.declare(self.url)
        queue = self.adapter.Queue(address.queue)
        queue.durable = False
        queue.declare(self.url)
        exchange.bind(queue, self.url)
        self.producer_reader(address)

    def test_custom_topic_exchange(self):
        print 'test custom (topic) exchange'
        address = Address('test_4.topic/test.4')
        exchange = self.adapter.Exchange(address.exchange, 'topic')
        exchange.durable = False
        exchange.auto_delete = True
        exchange.declare(self.url)
        queue = self.adapter.Queue(address.queue)
        queue.durable = False
        queue.declare(self.url)
        exchange.bind(queue, self.url)
        self.producer_reader(address)

    def test_crud(self):
        print 'test CRUD'
        queue = self.adapter.Queue('test.5')
        queue.durable = False
        queue.declare(self.url)
        exchange = self.adapter.Exchange('test_crud_5.direct', 'direct')
        exchange.declare(self.url)
        exchange.bind(queue, self.url)
        queue.delete(self.url)
        exchange.delete(self.url)

    def __call__(self):
        self.test_crud()
        self.test_no_exchange()
        self.test_direct_exchange()
        self.test_custom_direct_exchange()
        self.test_custom_topic_exchange()
        print 'DONE'