from time import time
from collections import deque
from uuid import uuid4

from proton import ConnectionException, Url, Timeout, Endpoint, LinkException
from proton.reactor import Container, Delivery
from proton.handlers import MessagingHandler

from gofer.common import utf8
from gofer.messaging.adapter.reliability import YEAR


class Condition(object):
    pass


class RemoteConnectionOpened(Condition):

    def __init__(self, connection):
        super(RemoteConnectionOpened, self).__init__()
        self.connection = connection

    def __call__(self):
        return not (self.connection.state & Endpoint.REMOTE_UNINIT)

    def __str__(self):
        return '[wait] remote connection opened: %s' % self.connection.url


class RemoteConnectionClosed(Condition):

    def __init__(self, connection):
        super(RemoteConnectionClosed, self).__init__()
        self.connection = connection

    def __call__(self):
        return not (self.connection.state & Endpoint.REMOTE_ACTIVE)

    def __str__(self):
        return '[wait] remote connection closed: %s' % self.connection.url


class RemoteLinkClosed(Condition):

    def __init__(self, link):
        super(RemoteLinkClosed, self).__init__()
        self.link = link

    def __call__(self):
        return not (self.link.state & Endpoint.REMOTE_ACTIVE)

    def __str__(self):
        return '[wait] remote link closed: %s' % self.link.name


class HasMessage(Condition):
    def __init__(self, handler):
        super(HasMessage, self).__init__()
        self.handler = handler

    def __call__(self):
        return self.handler.has_message()

    def __str__(self):
        return '[wait] next message: %s' % self.handler.link.name


class DeliverySettled(Condition):

    def __init__(self, link, delivery):
        super(DeliverySettled, self).__init__()
        self.link = link
        self.delivery = delivery

    def __call__(self):
        return self.delivery.settled()

    def __str__(self):
        return '[wait] delivery settled: %s' % self.link.name


class LinkDetached(LinkException):

    def __init__(self, link):
        super(LinkDetached, self).__init__(link.name)


class ConnectionClosed(ConnectionException):

    def __init__(self, connection):
        super(ConnectionClosed, self).__init__(connection.url)


class Connection(object):

    def __init__(self):
        self.container = Container()
        self.impl = None

    def is_open(self):
        return self.impl is not None

    def open(self, url, timeout=None, ssl_domain=None, heartbeat=None):
        if self.is_open():
            return
        impl = self.container.connect(
            url=Url(utf8(url)),
            handler=self,
            ssl_domain=ssl_domain,
            heartbeat=heartbeat,
            reconnect=False)
        condition = RemoteConnectionOpened(impl)
        self.wait(condition, timeout)
        self.impl = impl

    def wait(self, condition, timeout=None):
        started = time()
        remaining = timeout or YEAR
        while not condition():
            self.container.timeout = remaining
            self.container.process()
            duration = time() - started
            remaining -= duration
            if remaining <= 0:
                raise Timeout(str(condition))

    def close(self):
        if self.is_open():
            return
        try:
            self.impl.close()
            condition = RemoteConnectionClosed(self.impl)
            self.wait(condition)
        finally:
            self.impl = None

    def sender(self, address):
        sender = self.container.create_sender(self.impl, utf8(address), str(uuid4()))
        return Sender(self, sender)

    def receiver(self, address, credit=1, dynamic=False):
        handler = InboundHandler(self, credit)
        receiver = self.container.create_receiver(
            self.impl,
            utf8(address),
            name=str(uuid4()),
            dynamic=dynamic,
            handler=handler)
        return Receiver(self, receiver, handler, credit)


class Messenger(object):

    def __init__(self, connection, link):
        self.connection = connection
        self.link = link
        self.detect_closed()

    def detect_closed(self):
        if self.link.state & Endpoint.REMOTE_CLOSED:
            self.link.close()
            raise LinkDetached(self.link)


class Sender(Messenger):

    def __init__(self, connection, impl):
        super(Sender, self).__init__(connection, impl)

    def send(self, message, timeout=None):
        delivery = self.link.send(message)
        condition = DeliverySettled(self.link, delivery)
        self.connection.wait(condition, timeout)


class InboundHandler(MessagingHandler):

    def __init__(self, connection, prefetch):
        super(InboundHandler, self).__init__(prefetch, auto_accept=False)
        self.connection = connection
        self.inbound = deque()

    @property
    def has_message(self):
        return len(self.inbound)

    def pop(self):
        return self.inbound.popleft()

    def on_message(self, event):
        self.inbound.append((event.message, event.delivery))
        self.connection.container.yield_()

    def on_connection_error(self, event):
        raise ConnectionClosed(event.connection)

    def on_link_error(self, event):
        if event.link.state & Endpoint.LOCAL_ACTIVE:
            event.link.close()
            raise LinkDetached(event.link)


class Receiver(Messenger):

    def __init__(self, connection, impl, handler, credit=1):
        super(Receiver, self).__init__(connection, impl)
        self.handler = handler
        self.credit = credit
        if credit:
            impl.flow(credit)

    def get(self, timeout=None):
        if not self.link.credit:
            self.link.flow(self.credit)
        condition = HasMessage(self.handler)
        self.connection.wait(condition, timeout)
        return self.handler.pop()

    def accept(self, delivery):
        delivery.update(Delivery.ACCEPTED)
        delivery.settle()

    def reject(self, delivery):
        delivery.update(Delivery.REJECTED)
        delivery.settle()
