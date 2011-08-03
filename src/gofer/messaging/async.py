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


"""
Provides async AMQP message consumer classes.
"""

from time import sleep, time
from threading import Thread
from gofer import Singleton
from gofer.messaging import *
from gofer.messaging.dispatcher import Return, RemoteException
from gofer.messaging.policy import RequestTimeout
from gofer.messaging.consumer import Consumer
from gofer.messaging.producer import Producer
from gofer.messaging.store import Journal
from logging import getLogger

log = getLogger(__name__)


class ReplyConsumer(Consumer):
    """
    A request, reply consumer.
    @ivar listener: An reply listener.
    @type listener: any
    @ivar watchdog: An (optional) watchdog.
    @type watchdog: L{WatchDog}
    """

    def start(self, listener, watchdog=None):
        """
        Start processing messages on the queue and
        forward to the listener.
        @param listener: A reply listener.
        @type listener: L{Listener}
        @param watchdog: An (optional) watchdog.
        @type watchdog: L{WatchDog}
        """
        self.listener = listener
        self.watchdog = watchdog
        Consumer.start(self)

    def dispatch(self, envelope):
        """
        Dispatch received request.
        @param envelope: The received envelope.
        @type envelope: L{Envelope}
        """
        try:
            self.__notifywatchdog(envelope)
            reply = self.__getreply(envelope)
            reply.notify(self.listener)
        except Exception:
            log.error(envelope, exc_info=1)
            
    def __notifywatchdog(self, envelope):
        """
        Notify the watchdog that a proper reply has been
        received.  The effective timeout is incremented.
        @param envelope: The received envelope.
        @type envelope: L{Envelope}
        """
        if envelope.watchdog:
            return # sent by watchdog
        if self.watchdog is None:
            return
        try:
            self.watchdog.hack(envelope.sn)
        except Exception:
            log.error(envelope, exc_info=1)
        

    def __getreply(self, envelope):
        """
        Get the appropriate reply object.
        @param envelope: The received envelope.
        @type envelope: L{Envelope}
        @return: A reply object based on the recived envelope.
        @rtype: L{AsyncReply}
        """
        if envelope.status:
            return Status(envelope)
        result = Return(envelope.result)
        if result.succeeded():
            return Succeeded(envelope)
        else:
            return Failed(envelope)



class AsyncReply:
    """
    Asynchronous request reply.
    @ivar sn: The request serial number.
    @type sn: str
    @ivar origin: Which endpoint sent the reply.
    @type origin: str
    @ivar any: User defined (round-tripped) data.
    @type any: object
    """

    def __init__(self, envelope):
        """
        @param envelope: The received envelope.
        @type envelope: L{Envelope}
        """
        self.sn = envelope.sn
        self.origin = envelope.origin
        self.any = envelope.any

    def notify(self, listener):
        """
        Notify the specified listener.
        @param listener: The listener to notify.
        @type listener: L{Listener} or callable.
        """
        pass

    def __str__(self):
        s = []
        s.append(self.__class__.__name__)
        s.append('  sn : %s' % self.sn)
        s.append('  origin : %s' % self.origin)
        s.append('  user data : %s' % self.any)
        return '\n'.join(s)


class FinalReply(AsyncReply):
    """
    A (final) reply.
    """

    def notify(self, listener):
        if callable(listener):
            listener(self)
            return
        if self.succeeded():
            listener.succeeded(self)
        else:
            listener.failed(self)

    def succeeded(self):
        """
        Get whether the reply indicates success.
        @return: True when succeeded.
        @rtype: bool
        """
        return False

    def failed(self):
        """
        Get whether the reply indicates failure.
        @return: True when failed.
        @rtype: bool
        """
        return ( not self.succeeded() )

    def throw(self):
        """
        Throw contained exception.
        @raise Exception: When contained.
        """
        pass


class Succeeded(FinalReply):
    """
    Successful reply to asynchronous operation.
    @ivar retval: The returned value.
    @type retval: object
    """

    def __init__(self, envelope):
        """
        @param envelope: The received envelope.
        @type envelope: L{Envelope}
        """
        AsyncReply.__init__(self, envelope)
        reply = Return(envelope.result)
        self.retval = reply.retval

    def succeeded(self):
        return True

    def __str__(self):
        s = []
        s.append(AsyncReply.__str__(self))
        s.append('  retval:')
        s.append(str(self.retval))
        return '\n'.join(s)


class Failed(FinalReply):
    """
    Failed reply to asynchronous operation.  This reply
    indicates an exception was raised.
    @ivar exval: The returned exception.
    @type exval: object
    @see: L{Failed.throw}
    """

    def __init__(self, envelope):
        """
        @param envelope: The received envelope.
        @type envelope: L{Envelope}
        """
        AsyncReply.__init__(self, envelope)
        reply = Return(envelope.result)
        self.exval = RemoteException.instance(reply)

    def throw(self):
        raise self.exval

    def __str__(self):
        s = []
        s.append(AsyncReply.__str__(self))
        s.append('  exception:')
        s.append(str(self.exval))
        return '\n'.join(s)


class Status(AsyncReply):
    """
    Status changed for an asynchronous operation.
    @ivar status: The status.
    @type status: str
    @see: L{Failed.throw}
    """

    def __init__(self, envelope):
        """
        @param envelope: The received envelope.
        @type envelope: L{Envelope}
        """
        AsyncReply.__init__(self, envelope)
        self.status = 'started'

    def notify(self, listener):
        if callable(listener):
            listener(self)
        else:
            listener.status(self)

    def __str__(self):
        s = []
        s.append(AsyncReply.__str__(self))
        s.append('  status: %s' % str(self.status))
        return '\n'.join(s)


class Listener:
    """
    An asynchronous operation callback listener.
    """

    def succeeded(self, reply):
        """
        Async request succeeded.
        @param reply: The reply data.
        @type reply: L{Succeeded}.
        """
        pass

    def failed(self, reply):
        """
        Async request failed (raised an exception).
        @param reply: The reply data.
        @type reply: L{Failed}.
        """
        pass

    def status(self, reply):
        """
        Async request has started.
        @param reply: The request.
        @type reply: L{Status}.
        """
        pass


class WatchDog(Thread):
    """
    A watchdog thread used to track asynchronous messages
    by serial number.  Tracking is persisted using journal files.
    @ivar url: The AMQP broker URL.
    @type url: str
    @ivar __jnl: A journal use for persistence.
    @type __jnl: L{Journal}
    @ivar __producer: An AMQP message producer.
    @type __producer: L{Producer}
    @ivar __run: Run flag.
    @type __run: bool
    """
    
    __metaclass__ = Singleton
 
    URL = Producer.LOCALHOST

    def __init__(self, url=URL):
        """
        @param url: The (optional) broker URL.
        @type url: str
        """
        Thread.__init__(self, name='watchdog')
        self.url = url
        self.__jnl = Journal()
        self.__producer = None
        self.__run = True
        self.setDaemon(True)

    def run(self):
        """
        Begin tracking.
        """
        while True:
            try:
                self.process()
                sleep(1)
            except:
                log.error(self.getName(), exc_info=1)
                sleep(3)
    
    def stop(self):
        """
        Stop the thread.
        """
        self.__run = False
    
    def track(self, sn, replyto, any, timeout):
        """
        Add a request by serial number for tacking.
        @param sn: A serial number.
        @type sn: str
        @param replyto: An AMQP address.
        @type replyto: str
        @param any: User defined data.
        @type any: any
        @param timeout: A timeout (start,complete)
        @type timeout: tuple(2)
        """
        now = time()
        ts = (now+timeout[0], now+timeout[1])
        je = self.__jnl.write(sn, replyto, any, ts)
        log.info('tracking: %s', je)
            
    def hack(self, sn):
        """
        Timeout is a tuple of: (start,complete).
        Hack (increment) the index because a propery reply has been received.
        When the last timeout has been I{hacked}, the journal entry is
        removed from the list of I{tracked} messages.
        @param sn: An entry serial number.
        @type sn: str
        """
        log.info(sn)
        je = self.__jnl.find(sn)
        if not je:
            return
        je.idx += 1
        if je.idx < len(je.ts):
            je = self.__jnl.update(sn, idx=je.idx)
        else:
            self.__jnl.delete(sn)

    def process(self):
        """
        Process all I{outstanding} journal entries.
        When a journal entry (timeout) is detected, a L{RequestTimeout}
        exception is raised and sent to the I{replyto} AMQP address.
        The journal entry is deleted.
        """
        sent = []
        now = time()
        if self.__producer is None:
            self.__producer = Producer(url=self.url)
        for sn,je in self.__jnl.load().items():
            if now > je.ts[je.idx]:
                sent.append(sn)
                try:
                    raise RequestTimeout(sn, je.idx)
                except:
                    self.__overdue(je)
        for sn in sent:
            self.__jnl.delete(sn)
    
    def __overdue(self, je):
        """
        Send the (timeout) reply to the I{replyto} AMQP address
        specified in the journal entry.
        @param je: A journal entry.
        @type je: Entry
        """
        log.info('sn:%s timeout detected', je.sn)
        try:
            self.__sendreply(je)
        except:
            log.error(str(je), exc_info=1)
        
    def __sendreply(self, je):
        """
        Send the (timeout) reply to the I{replyto} AMQP address
        specified in the journal entry.
        @param je: A journal entry.
        @type je: Entry
        """
        sn = je.sn
        replyto = je.replyto
        any = je.any
        result = Return.exception()
        log.info('send (timeout) for sn:%s to:%s', sn, replyto)
        self.__producer.send(
            replyto,
            sn=sn,
            any=any,
            result=result,
            watchdog=self.__producer.uuid)
