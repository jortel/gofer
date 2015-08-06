from time import time
from collections import deque
from uuid import uuid4

from proton import ConnectionException, Url, Timeout, Endpoint, LinkException
from proton.reactor import Container, Delivery, DynamicNodeProperties
from proton.handlers import Handler, MessagingHandler

from gofer.common import utf8
from gofer.messaging.adapter.reliability import YEAR


class Condition(object):
    """
    Base wait condition.
    """
    pass


class ConnectionOpened(Condition):
    """
    Condition used to wait for the remote endpoint to be initialised.
    :ivar connection: The connection being opened.
    :type connection: proton.Connection
    """
    
    DESCRIPTION = 'connection opened'

    def __init__(self, connection):
        """
        :param connection: The connection being opened.
        :type connection: proton.Connection
        """
        super(ConnectionOpened, self).__init__()
        self.connection = connection

    def __call__(self):
        """
        Test the remote endpoint is initialized.
        :return: True if initialized.
        :rtype: bool
        """
        return not (self.connection.state & Endpoint.REMOTE_UNINIT)

    def __str__(self):
        return self.DESCRIPTION


class ConnectionClosed(Condition):
    """
    Condition used to wait for the remote endpoint to be inactive.
    :ivar connection: The connection being opened.
    :type connection: proton.Connection
    """
    
    DESCRIPTION = 'connection closed'

    def __init__(self, connection):
        """
        :param connection: The connection being closed.
        :type connection: proton.Connection
        """
        super(ConnectionClosed, self).__init__()
        self.connection = connection

    def __call__(self):
        """
        Test the remote endpoint is no longer active.
        :return: True if initialized.
        :rtype: bool
        """
        return not (self.connection.state & Endpoint.REMOTE_ACTIVE)

    def __str__(self):
        return self.DESCRIPTION


class LinkCondition(Condition):

    def __init__(self, link):
        super(LinkCondition, self).__init__()
        self.link = link

    @property
    def name(self):
        return self.link.name

    @property
    def address(self):
        if self.link.is_sender:
            return self.link.target.address
        else:
            return self.link.source.address


class LinkAttached(LinkCondition):

    DESCRIPTION = 'link attached: %s/%s'

    def __call__(self):
        return not (self.link.state & Endpoint.REMOTE_UNINIT)

    def __str__(self):
        return self.DESCRIPTION % (self.name, self.address)


class LinkDetached(LinkCondition):
    
    DESCRIPTION = 'link detached: %s'

    def __call__(self):
        return not (self.link.state & Endpoint.REMOTE_ACTIVE)

    def __str__(self):
        return self.DESCRIPTION % self.link.name


class HasMessage(Condition):
    
    DESCRIPTION = 'fetch: %s/%s'

    def __init__(self, receiver):
        super(HasMessage, self).__init__()
        self.receiver = receiver

    @property
    def name(self):
        return self.link.name

    @property
    def address(self):
        return self.link.source.address

    @property
    def link(self):
        return self.receiver.link

    def __call__(self):
        return len(self.receiver.handler)

    def __str__(self):
        return self.DESCRIPTION % (self.name, self.address)


class DeliverySettled(Condition):
    
    DESCRIPTION = 'delivery settled: %s'

    def __init__(self, link, delivery):
        super(DeliverySettled, self).__init__()
        self.link = link
        self.delivery = delivery

    def __call__(self):
        return self.delivery.settled

    def __str__(self):
        return self.DESCRIPTION % self.link.name


class ConnectionError(ConnectionException):

    def __init__(self, connection):
        super(ConnectionError, self).__init__(connection.url)


class LinkError(LinkException):

    DESCRIPTION = 'link: %s/%s failed: %s'

    def __init__(self, link):
        super(LinkError, self).__init__(repr(link))
        self.link = link

    @property
    def name(self):
        return self.link.name

    @property
    def address(self):
        if self.link.is_sender:
            return self.link.target.address
        else:
            return self.link.source.address

    @property
    def reason(self):
        if self.link.remote_condition:
            return self.link.remote_condition
        else:
            return 'by peer'

    def __str__(self):
        return self.DESCRIPTION % (self.name, self.address, self.reason)


class SendError(Exception):
    pass


class Messenger(object):

    def __init__(self, connection, link):
        self.connection = connection
        self.link = link
        self.connection.wait(LinkAttached(link))
        self.detect_closed()

    def detect_closed(self):
        if self.link.state & Endpoint.REMOTE_CLOSED:
            self.link.close()
            raise LinkError(self.link)

    def __getattr__(self, name):
        return getattr(self.link, name)


class Sender(Messenger):

    def __init__(self, connection, impl):
        super(Sender, self).__init__(connection, impl)

    def send(self, message, timeout=None):
        delivery = self.link.send(message)
        condition = DeliverySettled(self.link, delivery)
        self.connection.wait(condition, timeout)
        if delivery.remote_state in [Delivery.REJECTED, Delivery.RELEASED]:
            raise SendError()


class ReceiverHandler(MessagingHandler):

    def __init__(self, connection, prefetch):
        super(ReceiverHandler, self).__init__(prefetch, auto_accept=False)
        self.connection = connection
        self.inbound = deque()

    @property
    def container(self):
        return self.connection.container

    def pop(self):
        return self.inbound.popleft()

    def on_message(self, event):
        self.inbound.append((event.message, event.delivery))
        self.container.yield_()

    def on_connection_error(self, event):
        raise ConnectionError(event.connection)

    def on_link_error(self, event):
        if event.link.state & Endpoint.LOCAL_ACTIVE:
            event.link.close()
            raise LinkError(event.link)

    def __len__(self):
        return len(self.inbound)


class Receiver(Messenger):

    def __init__(self, connection, impl, handler, credit):
        super(Receiver, self).__init__(connection, impl)
        self.handler = handler
        self.credit = credit
        self.flow()

    def flow(self):
        if not self.link.credit:
            self.link.flow(self.credit)

    def get(self, timeout=None):
        self.flow()
        condition = HasMessage(self)
        self.connection.wait(condition, timeout)
        return self.handler.pop()

    def accept(self, delivery):
        delivery.update(Delivery.ACCEPTED)
        delivery.settle()

    def reject(self, delivery):
        delivery.update(Delivery.REJECTED)
        delivery.settle()


class Connection(Handler):

    def __init__(self, url):
        self.url = utf8(url)
        self.container = Container()
        self.container.start()
        self.impl = None

    def is_open(self):
        return self.impl is not None

    def open(self, timeout=None, ssl_domain=None, heartbeat=None):
        if self.is_open():
            return
        url = Url(self.url)
        url.defaults()
        impl = self.container.connect(
            url=url,
            handler=self,
            ssl_domain=ssl_domain,
            heartbeat=heartbeat,
            reconnect=False)
        condition = ConnectionOpened(impl)
        self.wait(condition, timeout)
        self.impl = impl

    def wait(self, condition, timeout=None):
        remaining = timeout or YEAR
        while not condition():
            started = time()
            self.container.timeout = remaining
            print 'process(): wait on: %s' % condition
            self.container.process()
            elapsed = time() - started
            remaining -= elapsed
            if remaining <= 0:
                raise Timeout(str(condition))

    def close(self):
        if self.is_open():
            return
        try:
            self.impl.close()
            condition = ConnectionClosed(self.impl)
            self.wait(condition)
        finally:
            self.impl = None

    def sender(self, address):
        name = str(uuid4())
        sender = self.container.create_sender(self.impl, utf8(address), name=name)
        return Sender(self, sender)

    def receiver(self, address, dynamic=False, credit=1):
        options = None
        name = str(uuid4())
        handler = ReceiverHandler(self, credit)
        if dynamic:
            # needed by dispatch router
            options = DynamicNodeProperties({'x-opt-qd.address': utf8(address)})
            address = None
        receiver = self.container.create_receiver(
            context=self.impl,
            source=utf8(address),
            name=name,
            dynamic=dynamic,
            handler=handler,
            options=options)
        return Receiver(self, receiver, handler, credit)

    def __enter__(self):
        self.open()
        return self

    def __exit__(self):
        self.close()


# -------------- TEST --------------------------------------------------------

from proton import Message


URL = 'amqp://localhost'
ADDRESS = 'jeff'


def send(connection, timeout=5):
    print 'send()'
    sender = connection.sender(ADDRESS)
    message = Message(body='hello')
    sender.send(message, timeout=timeout)
    print 'sent'


def receive(connection, timeout=5):
    print 'receive()'
    receiver = connection.receiver(ADDRESS)
    m, d = receiver.get(timeout=timeout)
    print m.body


if __name__ == '__main__':
    connection = Connection(URL)
    connection.open(timeout=5)
    print 'opened'
    send(connection)
    receive(connection)
    connection.close()
