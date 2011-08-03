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
from gofer import NAME
from gofer.messaging import *
from gofer.messaging.window import Window
from time import sleep
from stat import *
from threading import Thread, RLock
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

    ROOT = '/var/lib/%s/messaging' % NAME

    def __init__(self, id):
        """
        @param id: The queue id.
        @type id: str
        """
        self.id = id
        self.pending = []
        self.uncommitted = []
        self.__lock = RLock()
        self.mkdir()
        self.load()

    def add(self, envelope):
        """
        Enqueue the specified envelope.
        @param envelope: An L{Envelope}
        @type envelope: L{Envelope}
        """

        fn = self.fn(envelope)
        f = open(fn, 'w')
        f.write(envelope.dump())
        f.close()
        log.info('{%s} add pending:\n%s', self.id, envelope)
        self.lock()
        try:
            self.pending.insert(0, envelope)
        finally:
            self.unlock()

    def next(self, wait=1):
        """
        Get the next pending envelope.
        @param wait: The number of seconds to wait for a pending item.
        @type wait: int
        @return: An L{Envelope}
        @rtype: L{Envelope}
        """
        self.lock()
        try:
            queue = self.pending[:]
        finally:
            self.unlock()
        while wait:
            if queue:
                envelope = queue.pop()
                window = Window(envelope.window)
                if window.future():
                    log.info('{%s} deferring:\n%s', self.id, envelope)
                    continue
                self.remove(envelope)
                log.info('{%s} next:\n%s', self.id, envelope)
                return envelope
            else:
                sleep(1)
                wait -= 1

    def remove(self, envelope):
        """
        Remove the specified envelope and place on the uncommitted list.
        @param envelope: An L{Envelope}
        @type envelope: L{Envelope}
        """
        self.lock()
        try:
            self.pending.remove(envelope)
            self.uncommitted.append(envelope)
        finally:
            self.unlock()

    def commit(self):
        """
        Commit envelopes removed from the queue.
        @return: self
        @rtype: L{PendingQueue}
        """
        self.lock()
        try:
            uncommitted = self.uncommitted[:]
        finally:
            self.unlock()
        for envelope in uncommitted:
            fn = self.fn(envelope)
            log.info('{%s} commit:%s', self.id, envelope.sn)
            try:
                os.remove(fn)
            except Exception, e:
                log.exception(e)
        self.lock()
        try:
            self.uncommitted = []
        finally:
            self.unlock()
        return self

    def load(self):
        """
        Load the in-memory queue from filesystem.
        """

        path = os.path.join(self.ROOT, self.id)
        pending = []
        for fn in os.listdir(path):
            path = os.path.join(self.ROOT, self.id, fn)
            envelope = Envelope()
            f = open(path)
            s = f.read()
            f.close()
            envelope.load(s)
            ctime = self.created(path)
            pending.append((ctime, envelope))
        pending.sort()
        self.lock()
        try:
            self.pending = [p[1] for p in pending]
        finally:
            self.unlock()

    def created(self, path):
        """
        Get create timestamp.
        @return: The file create timestamp.
        @rtype: int
        """
        stat = os.stat(path)
        return stat[ST_CTIME]

    def modified(self, path):
        """
        Get modification timestamp.
        @return: The file modification timestamp.
        @rtype: int
        """
        stat = os.stat(path)
        return stat[ST_MTIME]

    def mkdir(self):
        """
        Ensure the directory exists.
        """
        path = os.path.join(self.ROOT, self.id)
        if not os.path.exists(path):
            os.makedirs(path)

    def fn(self, envelope):
        """
        Get the qualified file name for the envelope.
        @param envelope: An L{Envelope}
        @type envelope: L{Envelope}
        @return: The absolute file path.
        @rtype: str
        """
        return os.path.join(self.ROOT, self.id, envelope.sn)

    def lock(self):
        self.__lock.acquire()

    def unlock(self):
        self.__lock.release()


class PendingReceiver(Thread):
    """
    A pending queue receiver.
    @ivar __run: The main run loop flag.
    @type __run: bool
    @ivar queue: The L{PendingQueue} being read.
    @type queue: L{PendingQueue}
    @ivar consumer: The queue listener.
    @type consumer: L{gofer.messaging.consumer.Consumer}
    """

    def __init__(self, queue, listener):
        self.__run = True
        self.queue = queue
        self.listener = listener
        Thread.__init__(self, name='pending:%s' % queue.id)
        self.setDaemon(True)

    def run(self):
        """
        Main receiver (thread).
        Read and dispatch envelopes.
        """
        log.info('started')
        while self.__run:
            envelope = self.queue.next(3)
            if envelope:
                self.dispatch(envelope)
                self.queue.commit()
        log.info('stopped')

    def dispatch(self, envelope):
        """
        Dispatch the envelope to the listener.
        @param envelope: An L{Envelope} to be dispatched.
        @type envelope: L{Envelope}
        """
        try:
            self.listener.dispatch(envelope)
        except Exception, e:
            log.exception(e)

    def stop(self):
        """
        Stop the receiver.
        """
        self.__run = False

    
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
    
    def __init__(self, root=ROOT):
        """
        @param ctag: A correlation tag.
        @type ctag: str
        """
        self.root = root
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
