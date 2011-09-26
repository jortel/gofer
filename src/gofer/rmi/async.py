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

import os
from time import sleep, time
from threading import Thread
from gofer import NAME, Singleton
from gofer.messaging import *
from gofer.rmi.dispatcher import Return, RemoteException
from gofer.rmi.policy import RequestTimeout
from gofer.messaging.consumer import Consumer
from gofer.messaging.producer import Producer
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
        self.origin = envelope.routing[0]
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


class WatchDog:
    """
    A watchdog object used to track asynchronous messages
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
    DOMAIN = 'watchdog'

    def __init__(self, url=URL):
        """
        @param url: The (optional) broker URL.
        @type url: str
        """
        self.url = url
        self.__jnl = Journal(self.DOMAIN)
        self.__producer = None
        
    def start(self):
        """
        Start a watchdog thread.
        @return: The started thread.
        @rtype: L{WatchDogThread}
        """
        thread = WatchDogThread(self)
        thread.start()
        return thread
    
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
        
        
class WatchDogThread(Thread):
    """
    Watchdog thread.
    """

    def __init__(self, watchdog):
        Thread.__init__(self, name='watchdog')
        self.watchdog = watchdog
        self.__run = True
        self.setDaemon(True)

    def run(self):
        watchdog = self.watchdog
        while self.__run:
            try:
                watchdog.process()
                sleep(1)
            except:
                log.error(self.getName(), exc_info=1)
                sleep(3)
                
    def stop(self):
        self.__run = False
        return self


class Journal:
    """
    Async message journal
    Entry:
      - sn: serial number
      - replyto: reply to amqp address.
      - any: user data
      - timeout: (start<ctime>, complte<ctime>)
      - idx: current timout index.
    """
    
    ROOT = '/var/lib/%s/journal' % NAME
    
    def __init__(self, domain):
        """
        @param domain: A journal domain (subdir).
        @type domain: str
        """
        self.root = os.path.join(self.ROOT, domain)
        self.__mkdir()
        
    def load(self):
        """
        Load all journal entries.
        @return: A dict of journal entries.
        @rtype: dict
        """
        entries = {}
        for fn in os.listdir(self.root):
            path = os.path.join(self.root, fn)
            je = self.__read(path)
            if not je:
                continue
            entries[je.sn] = je
        return entries
        
    def write(self, sn, replyto, any, ts):
        """
        Write a new journal entry.
        @param sn: A serial number.
        @type sn: str
        @param replyto: An AMQP address.
        @type replyto: str
        @param any: User defined data.
        @type any: any
        @param ts: A timeout (start<ctime>,complete<ctime>)
        @type ts: tuple(2)
        """
        je = Envelope(
            sn=sn,
            replyto=replyto,
            any=any,
            ts=ts,
            idx=0)
        self.__write(je)
        return je
            
    def update(self, sn, **property):
        """
        Update a journal entry for the specified I{sn}.
        @param sn: An entry serial number.
        @type sn: str
        @param property: properties to update.
        @type property: dict
        @return: The updated journal entry
        @rtype: Entry
        @raise KeyError: On invalid key.
        """
        je = self.find(sn)
        if not je:
            return None
        for k,v in property.items():
            if k in ('sn',):
                continue
            if k in je:
                je[k] = v
            else:
                raise KeyError(k)
        self.__write(je)
        return je
        
    def delete(self, sn):
        """
        Delete a journal entry by serial number.
        @param sn: An entry serial number.
        @type sn: str
        """
        fn = self.__fn(sn)
        path = os.path.join(self.root, fn)
        self.__unlink(path)
        
    def find(self, sn):
        """
        Find a journal entry my serial number.
        @param sn: An entry serial number.
        @type sn: str
        @return: The journal entry.
        @rtype: Entry
        """
        try:
            fn = self.__fn(sn)
            path = os.path.join(self.root, fn)
            return self.__read(path)
        except OSError:
            log.error(sn)
    
    def __fn(self, sn):
        """
        File name.
        @param sn: An entry serial number.
        @type sn: str
        @return: The journal file name by serial number.
        @rtype: str
        """
        return '%s.jnl' % sn
    
    def __read(self, path):
        """
        Read the journal file at the specified I{path}.
        @param path: A journal file path.
        @type path: str
        @return: A journal entry.
        @rtype: Entry
        """
        f = open(path)
        try:
            try:
                je = Envelope()
                je.load(f.read())
                return je
            except:
                log.error(path, exc_info=1)
                self.__unlink(path)
        finally:
            f.close()
            
    def __write(self, je):
        """
        Write the specified journal entry.
        @param je: A journal entry
        @type je: Entry
        """
        path = os.path.join(self.root, self.__fn(je.sn))
        f = open(path, 'w')
        try:
            f.write(je.dump())
        finally:
            f.close 
    
    def __unlink(self, path):
        """
        Unlink (delete) the journal file at the specified I{path}.
        @param path: A journal file path.
        @type path: str
        """
        try:
            os.unlink(path)
        except OSError:
            log.error(path, exc_info=1)
    
    def __mkdir(self):
        """
        Ensure the directory exists.
        """
        if not os.path.exists(self.root):
            os.makedirs(self.root)
