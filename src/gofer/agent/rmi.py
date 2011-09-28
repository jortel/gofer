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

from time import time
from gofer.rmi.window import *
from gofer.rmi.store import PendingThread
from gofer.rmi.dispatcher import Dispatcher, Return
from gofer.rmi.threadpool import Immediate
from gofer.messaging import Envelope
from gofer.messaging.producer import Producer
from gofer.metrics import Timer
from logging import getLogger

log = getLogger(__name__)


class Expired(Exception):
    """
    TTL expired.
    """
    pass


class Task:
    """
    An RMI task to be scheduled on the plugin's thread pool.
    @ivar plugin: A plugin.
    @type plugin: Plugin
    @ivar envelope: A gofer messaging envelope.
    @type envelope: L{Envelope}
    @ivar producer: An AMQP message producer.
    @type producer: L{Producer}
    @ivar window: The window in which the task is valid.
    @type window: dict
    @ivar ttl: The task time-to-live.
    @type ttl: float
    @ivar ts: Timestamp
    @type ts: float
    """
    
    def __init__(self, plugin, envelope, producer, commit):
        """
        @param plugin: A plugin.
        @type plugin: Plugin
        @param envelope: A gofer messaging envelope.
        @type envelope: L{Envelope}
        @param producer: An AMQP message producer.
        @type producer: L{Producer}
        @param commit: Transaction commit function.
        @type commit: callable
        """
        self.plugin = plugin
        self.envelope = envelope
        self.producer = producer
        self.commit = commit
        self.window = envelope.window
        self.ttl = envelope.ttl
        self.ts = time()
        
    def __call__(self, *args, **options):
        """
        Dispatch received request.
        """
        envelope = self.envelope
        try:
            self.expired()
            self.windowmissed()
            self.sendstarted(envelope)
            result = self.plugin.dispatch(envelope)
            self.commit(envelope.sn)
            self.sendreply(envelope, result)
        except Expired:
            self.commit(envelope.sn)
            log.info('expired:\n%s', envelope)
        except WindowMissed:
            self.commit(envelope.sn)
            log.info('window missed:\n%s', envelope)
            self.sendreply(envelope, Return.exception())
        except WindowPending:
            pass # ignored
        
    def windowmissed(self):
        """
        Check the window.
        @raise WindowPending: when window in the future.
        @raise WindowMissed: when window missed.
        """
        w = self.window
        if not isinstance(w, dict):
            return
        window = Window(w)
        envelope = self.envelope
        if window.future():
            pending = self.__pending.queue
            pending.add(envelope)
            raise WindowPending(envelope.sn)
        if window.past():
            raise WindowMissed(envelope.sn)
        
    def expired(self):
        """
        Check the TTL.
        @raise Expired: When TTL expired.
        """
        ttl = self.ttl
        if not isinstance(ttl, float):
            return
        elapsed = (time()-self.ts)
        if elapsed > ttl:
            raise Expired()
    
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
        ts = envelope.ts
        now = time()
        duration = Timer(ts, now)
        replyto = envelope.replyto
        log.info('%s processed in: %s', sn, duration)
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
            

class EmptyPlugin:
    """
    An I{empty} plugin.
    Used when the appropriate plugin cannot be found.
    """
    
    def getpool(self):
        return Immediate()
    
    def provides(self, classname):
        return False
    
    def dispatch(self, request):
        d = Dispatcher({})
        return d.dispatch(request)
    

class Scheduler(PendingThread):
    """
    The pending request scheduler.
    Processes the I{pending} queue.
    @ivar plugins: A collection of loaded plugins.
    @type plugins: list
    @ivar producers: A cache of AMQP producers.
    @type producers: dict
    """
    
    def __init__(self, plugins):
        """
        @param plugins: A collection of loaded plugins.
        @type plugins: list
        """
        PendingThread.__init__(self)
        self.plugins = plugins
        self.producers = {}
        
    def dispatch(self, envelope):
        """
        Dispatch the specified envelope to plugin that
        provides the specified class.
        @param envelope: A gofer messaging envelope.
        @type envelope: L{Envelope}
        """
        url = envelope.url
        plugin = self.findplugin(envelope)
        task = Task(
            plugin,
            envelope,
            self.producer(url),
            self.commit)
        pool = plugin.getpool()
        pool.run(task)
        
    def findplugin(self, envelope):
        """
        Find the plugin that provides the class specified in
        the I{request} embedded in the envelope.  Returns
        L{EmptyPlugin} when not found.
        @param envelope: A gofer messaging envelope.
        @type envelope: L{Envelope}
        @return: The appropriate plugin.
        @rtype: Plugin
        """
        request = Envelope(envelope.request)
        classname = request.classname 
        for plugin in self.plugins:
            if plugin.provides(classname):
                return plugin
        return EmptyPlugin()
    
    def producer(self, url):
        """
        Find the cached producer by URL.
        @param url: The URL of the broker the request was received.
        @type url: str
        @return: The appropriate producer.
        @rtype: L{Producer}
        """
        p = self.producers.get(url)
        if p is None:
            p = Producer(url=url)
            self.producers[url] = p
        return p