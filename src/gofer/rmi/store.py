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
Provides (local) message storage classes.
"""

import os
from stat import *
from gofer import NAME, Singleton
from gofer.messaging import *
from gofer.rmi.window import Window
from time import time
from threading import Thread, RLock, Event
from logging import getLogger

log = getLogger(__name__)


class PendingQueue:
    """
    Persistent (local) storage of I{pending} envelopes that have
    been processed of an AMQP queue.  Most likely use is for messages
    with a future I{window} which cannot be processed immediately.
    @cvar ROOT: The root directory used for storage.
    @type ROOT: str
    @ivar id: The queue id.
    @type id: str
    @ivar lastmod: Last (directory) modification.
    @type lastmod: int
    @ivar pending: The queue of pending envelopes.
    @type pending: [Envelope,..]
    @ivar uncommitted: A list (removed) of files pending commit.
    @type uncommitted: [path,..]
    """
    
    __metaclass__ = Singleton

    ROOT = '/var/lib/%s/messaging/pending' % NAME

    def __init__(self):
        self.__pending = []
        self.__uncommitted = {}
        self.__mutex = RLock()
        self.__event = Event()
        self.__mkdir()
        self.__load()

    def add(self, url, envelope):
        """
        Enqueue the specified envelope.
        @param url: The broker URL.
        @type url: str
        @param envelope: An L{Envelope}
        @type envelope: L{Envelope}
        """
        envelope.ts = time()
        envelope.url = url
        fn = self.__fn(envelope)
        f = open(fn, 'w')
        f.write(envelope.dump())
        f.close()
        log.debug('add pending:\n%s', envelope)
        self.__lock()
        try:
            self.__pending.insert(0, envelope)
        finally:
            self.__unlock()
        self.__event.set()

    def get(self, wait=10):
        """
        Get the next pending envelope.
        @param wait: The number of seconds to block.
        @type wait: int
        @return: An L{Envelope}
        @rtype: L{Envelope}
        """
        assert(wait >= 0)
        try:
            return self.__get(wait)
        finally:
            self.__event.clear()
                
    def commit(self, sn):
        """
        Commit an entry returned by get().
        @param sn: The serial number to commit.
        @type sn: str
        @raise KeyError: when no found.
        """
        self.__lock()
        try:
            log.debug('commit: %s', sn)
            envelope = self.__uncommitted.pop(sn)
            fn = self.__fn(envelope)
            os.unlink(fn)
        finally:
            self.__unlock()

    def __purge(self, envelope):
        """
        Purge the queue entry.
        @param envelope: An L{Envelope}
        @type envelope: L{Envelope}
        """
        self.__lock()
        try:
            log.info('purge:%s', envelope.sn)
            fn = self.__fn(envelope)
            os.unlink(fn)
            self.__pending.remove(envelope)
        finally:
            self.__unlock()

    def __pendingcommit(self, envelope):
        """
        Move the envelope to the uncommitted list.
        @param envelope: An L{Envelope}
        @type envelope: L{Envelope}
        """
        self.__lock()
        try:
            self.__pending.remove(envelope)
            self.__uncommitted[envelope.sn] = envelope
        finally:
            self.__unlock()

    def __load(self):
        """
        Load the in-memory queue from filesystem.
        """
        path = os.path.join(self.ROOT)
        pending = []
        for fn in os.listdir(path):
            path = os.path.join(self.ROOT, fn)
            envelope = self.__import(path)
            if not envelope:
                continue
            ctime = self.__created(path)
            pending.append((ctime, envelope))
        pending.sort()
        self.__lock()
        try:
            self.__pending = [p[1] for p in pending]
        finally:
            self.__unlock()
            
    def __import(self, path):
        """
        Import a stored envelpoe.
        @param path: An absolute file path.
        @type path: str
        @return: An imported envelope.
        @rtype: L{Envelope}
        """
        try:
            s = self.__read(path)
            envelope = Envelope()
            envelope.load(s)
            return envelope
        except:
            log.exception(path)
            log.error('%s, discarded', path)
            os.unlink(path)
            
    def __get(self, wait=1):
        """
        Get the next pending envelope.
        @param wait: The number of seconds to wait for a pending item.
        @type wait: int
        @return: (url, L{Envelope})
        @rtype: L{Envelope}
        """
        while wait:
            queue = self.__copy(self.__pending)
            popped = self.__pop(queue)
            if popped:
                log.debug('popped: (%s) %s', popped.url, popped.sn)
                return popped
            else:
                wait -= 1
                self.__event.wait(1)
            
    def __pop(self, queue):
        """
        Pop and return the next I{ready} entry.
        Entries that have expired (TTL), are purged.
        Entries that have a future I{window} are excluded.
        @param queue: An ordered list of candidate entries.
        @type queue: list
        @return: An L{Envelope}
        @rtype: L{Envelope}
        """
        popped = None
        while queue:
            envelope = queue.pop()
            try:
                if self.__expired(envelope):
                    self.__purge(envelope)
                    continue # TTL expired
                if self.__delayed(envelope):
                    continue # future
                self.__pendingcommit(envelope)
                self.__adjustTTL(envelope)
                popped = envelope
                break
            except Exception:
                log.error(envelope, exc_info=1)
                self.__purge(envelope)
        return popped
            
    def __mkdir(self):
        """
        Ensure the directory exists.
        """
        path = self.ROOT
        if not os.path.exists(path):
            os.makedirs(path)

    def __created(self, path):
        """
        Get create timestamp.
        @return: The file create timestamp.
        @rtype: int
        """
        stat = os.stat(path)
        return stat[ST_CTIME]

    def __modified(self, path):
        """
        Get modification timestamp.
        @return: The file modification timestamp.
        @rtype: int
        """
        stat = os.stat(path)
        return stat[ST_MTIME]

    def __fn(self, envelope):
        """
        Get the qualified file name for an entry.
        @param envelope: A queue entry.
        @type envelope: L{Envelope}
        @return: The absolute file path.
        @rtype: str
        """
        return os.path.join(self.ROOT, envelope.sn)
    
    def __expired(self, envelope):
        """
        Get whether the envelope has expired.
        @param envelope: A queue entry.
        @type envelope: L{Envelope}
        @return: True when expired based on TTL.
        @rtype: bool
        """
        now = time()
        if isinstance(envelope.ttl, float):
            elapsed = (now-envelope.ts)
            if envelope.ttl < elapsed:
                log.info('expired:\n%s', envelope)
                return True
        return False
    
    def __adjustTTL(self, envelope):
        """
        Adjust the TTL based on time spent on the queue.
        @param envelope: A queue entry.
        @type envelope: L{Envelope}
        """
        if isinstance(envelope.ttl, float):
            elapsed = (time()-envelope.ts)
            envelope.ttl -= elapsed
    
    def __delayed(self, envelope):
        """
        Get whether the envelope has a future window.
        @param envelope: An L{Envelope}
        @type envelope: L{Envelope}
        @return: True when window in the future.
        @rtype: bool
        """
        if envelope.window:
            window = Window(envelope.window)
            if window.future():
                log.info('deferring:\n%s', envelope)
                return True
        return False
    
    def __copy(self, collection):
        self.__lock()
        try:
            return collection[:]
        finally:
            self.__unlock()

    def __read(self, path):
        f = open(path)
        try:
            return f.read()
        finally:
            f.close()

    def __lock(self):
        self.__mutex.acquire()

    def __unlock(self):
        self.__mutex.release()


class PendingThread(Thread):
    """
    A pending queue receiver.
    @ivar __run: The main run loop flag.
    @type __run: bool
    @ivar queue: The L{PendingQueue} being read.
    @type queue: L{PendingQueue}
    @ivar consumer: The queue listener.
    @type consumer: L{gofer.messaging.consumer.Consumer}
    """

    def __init__(self):
        self.__run = True
        self.queue = PendingQueue()
        Thread.__init__(self, name='pending')
        self.setDaemon(True)

    def run(self):
        """
        Main receiver (thread).
        Read and dispatch envelopes.
        """
        log.info('started')
        while self.__run:
            envelope = self.queue.get(3)
            if not envelope:
                continue
            self.dispatch(envelope)
        log.info('stopped')
        
    def dispatch(self, envelope):
        """
        Dispatch the envelope.
        @param envelope: An L{Envelope}
        @type envelope: L{Envelope}        
        """
        pass
    
    def commit(self, sn):
        """
        Commit a dispatched envelope.
        @param sn: The serial number to commit.
        @type sn: str
        """
        try:
            self.queue.commit(sn)
        except KeyError:
            log.error('%s, not valid for commit', sn)

    def stop(self):
        """
        Stop the receiver.
        """
        self.__run = False