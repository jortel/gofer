#
# Copyright (c) 2010 Red Hat, Inc.
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

"""
Provides AMQP message consumer classes.
"""

from gofer.messaging import *
from gofer.messaging.endpoint import Endpoint
from gofer.messaging.producer import Producer
from gofer.messaging.dispatcher import Request, Return
from gofer.messaging.window import *
from gofer.messaging.store import PendingQueue, PendingReceiver
from qpid.messaging import Empty
from threading import Thread
from logging import getLogger

log = getLogger(__name__)


class ReceiverThread(Thread):
    """
    Consumer (worker) thread.
    @ivar __run: The main run/read flag.
    @type __run: bool
    @ivar consumer: A consumer that is notified when
        messages are read.
    @type consumer: L{Consumer}
    """
    
    WAIT = 3

    def __init__(self, consumer):
        """
        @param consumer: A consumer that is notified when
            messages are read.
        @type consumer: L{Consumer}
        """
        self.__run = True
        self.consumer = consumer
        Thread.__init__(self, name=consumer.id())
        self.setDaemon(True)

    def run(self):
        """
        Messages are read from consumer.receiver and
        dispatched to the consumer.received().
        """
        msg = None
        while self.__run:
            try:
                msg = self.__fetch()
                if msg:
                    self.consumer.received(msg)
                log.debug('ready')
            except:
                log.error('failed:\n%s', msg, exc_info=True)

    def stop(self):
        """
        Stop reading the receiver and terminate
        the thread.
        """
        self.__run = False
        
    def __fetch(self):
        """
        Fetch the next message.
        @return: The next message or None.
        @rtype: Message
        """
        try:
            return self.receiver.fetch(timeout=self.WAIT)
        except Empty:
            pass
        except:
            log.error('failed', exc_info=True)
            sleep(self.WAIT)
    
    @property
    def receiver(self):
        return self.consumer.receiver


class Consumer(Endpoint):
    """
    An AMQP (abstract) consumer.
    """

    def __init__(self, destination, **other):
        """
        @param destination: The destination to consumer.
        @type destination: L{Destination}
        """
        self.destination = destination
        Endpoint.__init__(self, **other)

    def id(self):
        """
        Get the endpoint id
        @return: The destination (simple) address.
        @rtype: str
        """
        return repr(self.destination)

    def address(self):
        """
        Get the AMQP address for this endpoint.
        @return: The AMQP address.
        @rtype: str
        """
        return str(self.destination)

    def open(self):
        """
        Open and configure the consumer.
        """
        session = self.session()
        address = self.address()
        log.info('{%s} opening %s', self.id(), address)
        receiver = session.receiver(address)
        self.receiver = receiver

    def start(self):
        """
        Start processing messages on the queue.
        """
        self.thread = ReceiverThread(self)
        self.thread.start()

    def stop(self):
        """
        Stop processing requests.
        """
        try:
            self.thread.stop()
            self.thread.join(90)
        except:
            pass

    def close(self):
        """
        Stop the worker thread and clean up resources.
        """
        self.stop()
        self.receiver.close()

    def join(self):
        """
        Join the worker thread.
        """
        self.thread.join()

    def received(self, message):
        """
        Process received request.
        Inject subject & destination.uuid.
        @param message: The received message.
        @type message: qpid.messaging.Message
        """
        envelope = Envelope()
        subject = self.__subject(message)
        envelope.load(message.content)
        if subject:
            envelope.subject = subject
        envelope.destination = Options(uuid=repr(self.destination))
        log.debug('{%s} received:\n%s', self.id(), envelope)
        if self.valid(envelope):
            self.dispatch(envelope)
        self.ack()

    def valid(self, envelope):
        """
        Check to see if the envelope is valid.
        @param envelope: The received envelope.
        @type envelope: qpid.messaging.Message
        """
        valid = True
        if envelope.version != version:
            valid = False
            log.warn('{%s} version mismatch (discarded):\n%s',
                self.id(), envelope)
        return valid

    def dispatch(self, envelope):
        """
        Dispatch received request.
        @param envelope: The received envelope.
        @type envelope: qpid.messaging.Message
        """
        pass

    def __subject(self, message):
        """
        Extract the message subject.
        @param message: The received message.
        @type message: qpid.messaging.Message
        @return: The message subject
        @rtype: str
        """
        return message.properties.get('qpid.subject')


class Reader(Consumer):

    def start(self):
        pass

    def stop(self):
        pass

    def next(self, timeout=90):
        """
        Get the next envelope from the queue.
        @param timeout: The read timeout.
        @type timeout: int
        @return: The next envelope.
        @rtype: L{Envelope}
        """
        try:
            message = self.receiver.fetch(timeout=timeout)
            envelope = Envelope()
            envelope.load(message.content)
            log.debug('{%s} read next:\n%s', self.id(), envelope)
            return envelope
        except Empty:
            pass

    def search(self, sn, timeout=90):
        """
        Seach the reply queue for the envelope with
        the matching serial #.
        @param sn: The expected serial number.
        @type sn: str
        @param timeout: The read timeout.
        @type timeout: int
        @return: The next envelope.
        @rtype: L{Envelope}
        """
        log.debug('{%s} searching for: sn=%s', self.id(), sn)
        while True:
            envelope = self.next(timeout)
            if not envelope:
                return
            if sn == envelope.sn:
                log.debug('{%s} search found:\n%s', self.id(), envelope)
                return envelope
            else:
                log.debug('{%s} search discarding:\n%s', self.id(), envelope)
                self.ack()
                

class RequestConsumer(Consumer):
    """
    An AMQP request consumer.
    @ivar producer: A reply producer.
    @type producer: L{gofer.messaging.producer.Producer}
    @ivar dispatcher: An RMI dispatcher.
    @type dispatcher: L{gofer.messaging.dispatcher.Dispatcher}
    """

    def start(self, dispatcher):
        """
        Start processing messages on the queue using the
        specified dispatcher.
        @param dispatcher: An RMI dispatcher.
        @type dispatcher: L{gofer.messaging.Dispatcher}
        """
        q = PendingQueue(self.id())
        self.pending = PendingReceiver(q, self)
        self.dispatcher = dispatcher
        self.producer = Producer(url=self.url)
        Consumer.start(self)
        self.pending.start()

    def dispatch(self, envelope):
        """
        Dispatch received request.
        @param envelope: The received envelope.
        @type envelope: L{Envelope}
        """
        try:
            self.checkwindow(envelope)
            request = Request()
            request.update(envelope.request)
            request.auth = Options(
                uuid=envelope.destination.uuid,
                secret=envelope.secret,)
            self.sendstarted(envelope)
            result = self.dispatcher.dispatch(request)
        except WindowMissed:
            result = Return.exception()
        except WindowPending:
            return
        self.sendreply(envelope, result)

    def sendreply(self, envelope, result):
        """
        Send the reply if requested.
        @param envelope: The received envelope.
        @type envelope: L{Envelope}
        @param result: The request result.
        @type result: object
        """
        sn = envelope.sn
        any = envelope.any
        replyto = envelope.replyto
        if not replyto:
            return
        try:
            self.producer.send(
                replyto,
                sn=sn,
                any=any,
                result=result)
        except:
            log.error('send failed:\n%s', result, exc_info=True)

    def sendstarted(self, envelope):
        """
        Send the a status update if requested.
        @param envelope: The received envelope.
        @type envelope: L{Envelope}
        """
        sn = envelope.sn
        any = envelope.any
        replyto = envelope.replyto
        if not replyto:
            return
        try:
            self.producer.send(
                replyto,
                sn=sn,
                any=any,
                status='started')
        except:
            log.error('send (started), failed', exc_info=True)

    def checkwindow(self, envelope):
        """
        Check the window.
        @param envelope: The received envelope.
        @type envelope: L{Envelope}
        """
        w = envelope.window
        if not isinstance(w, dict):
            return
        window = Window(w)
        if window.future():
            pending = self.pending.queue
            pending.add(envelope)
            raise WindowPending(envelope.sn)
        if window.past():
            raise WindowMissed(envelope.sn)

    def __del__(self):
        try:
            self.pending.stop()
            self.pending.join(10)
        except:
            pass
