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
from threading import local as Local

from gofer.rmi.window import *
from gofer.rmi.tracker import Tracker
from gofer.rmi.store import PendingThread
from gofer.rmi.dispatcher import Dispatcher, Return
from gofer.rmi.threadpool import Immediate
from gofer.messaging.model import Envelope
from gofer.messaging import Producer
from gofer.transport.model import Destination
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
    :ivar plugin: A plugin.
    :type plugin: Plugin
    :ivar envelope: A gofer messaging envelope.
    :type envelope: Envelope
    :ivar producer: An AMQP message producer.
    :type producer: Producer
    :ivar window: The window in which the task is valid.
    :type window: dict
    :ivar ttl: The task time-to-live.
    :type ttl: float
    :ivar ts: Timestamp
    :type ts: float
    """
    
    context = Local()

    def __init__(self, plugin, envelope, commit):
        """
        :param plugin: A plugin.
        :type plugin: Plugin
        :param envelope: A gofer messaging envelope.
        :type envelope: Envelope
        :param commit: Transaction commit function.
        :type commit: callable
        """
        self.plugin = plugin
        self.envelope = envelope
        self.commit = commit
        self.window = envelope.window
        self.ttl = envelope.ttl
        self.ts = time()
        
    def __call__(self, *args, **options):
        """
        Dispatch received request.
        """
        envelope = self.envelope
        self.context.sn = envelope.sn
        self.context.progress = Progress(self)
        self.context.cancelled = Cancelled(envelope.sn)
        try:
            self.__call()
        finally:
            self.context.sn = None
            self.context.progress = None
            self.context.cancelled = None

    def __call(self):
        """
        Dispatch received request.
        """
        envelope = self.envelope
        try:
            self.expired()
            self.missed()
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

    def missed(self):
        """
        Check the window.
        :raise WindowPending: when window in the future.
        :raise WindowMissed: when window missed.
        """
        w = self.window
        if not isinstance(w, dict):
            return
        window = Window(w)
        envelope = self.envelope
        if window.past():
            raise WindowMissed(envelope.sn)
        
    def expired(self):
        """
        Check the TTL.
        :raise Expired: When TTL expired.
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
        :param envelope: The received envelope.
        :type envelope: Envelope
        """
        sn = envelope.sn
        any = envelope.any
        replyto = envelope.replyto
        if not replyto:
            return
        try:
            producer = Producer(url=envelope.url)
            try:
                producer.send(
                    Destination.create(replyto),
                    sn=sn,
                    any=any,
                    status='started')
            finally:
                producer.close()
        except:
            log.exception('send (started), failed')
            
    def sendreply(self, envelope, result):
        """
        Send the reply if requested.
        :param envelope: The received envelope.
        :type envelope: Envelope
        :param result: The request result.
        :type result: object
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
            producer = Producer(url=envelope.url)
            try:
                producer.send(
                    Destination.create(replyto),
                    sn=sn,
                    any=any,
                    result=result)
            finally:
                producer.close()
        except:
            log.exception('send failed:\n%s', result)
            

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
    :ivar plugins: A collection of loaded plugins.
    :type plugins: list
    :ivar producers: A cache of AMQP producers.
    :type producers: dict
    """
    
    def __init__(self, plugins):
        """
        :param plugins: A collection of loaded plugins.
        :type plugins: list
        """
        PendingThread.__init__(self)
        self.plugins = plugins
        
    def dispatch(self, envelope):
        """
        Dispatch the specified envelope to plugin that
        provides the specified class.
        :param envelope: A gofer messaging envelope.
        :type envelope: Envelope
        """
        plugin = self.findplugin(envelope)
        task = Task(plugin, envelope, self.commit)
        pool = plugin.getpool()
        pool.run(task)
        
    def findplugin(self, envelope):
        """
        Find the plugin that provides the class specified in
        the I{request} embedded in the envelope.  Returns
        EmptyPlugin when not found.
        :param envelope: A gofer messaging envelope.
        :type envelope: Envelope
        :return: The appropriate plugin.
        :rtype: Plugin
        """
        request = Envelope(envelope.request)
        classname = request.classname 
        for plugin in self.plugins:
            if plugin.provides(classname):
                return plugin
        return EmptyPlugin()
    

class Context:
    """
    Remote method invocation context.
    Provides call context to method implementations.
    :cvar current: The current call context.
    :type current: Local
    """
    
    @classmethod
    def current(cls):
        return Task.context


class Progress:
    """
    Provides support for progress reporting.
    :ivar __task: The current task.
    :type __task: Task
    :ivar total: The total work units.
    :type total: int
    :ivar completed: The completed work units.
    :type completed: int
    :ivar details: The reported details.
    :type details: object
    """
    
    def __init__(self, task):
        """
        :param task: The current task.
        :type task: Task
        """
        self.__task = task
        self.total = 0
        self.completed = 0
        self.details = {}

    def report(self):
        """
        Send the progress report.
        """
        sn = self.__task.envelope.sn
        any = self.__task.envelope.any
        replyto = self.__task.envelope.replyto
        if not replyto:
            return
        try:
            url = self.__task.envelope.url
            producer = Producer(url=url)
            try:
                producer.send(
                    Destination.create(replyto),
                    sn=sn,
                    any=any,
                    status='progress',
                    total=self.total,
                    completed=self.completed,
                    details=self.details)
            finally:
                producer.close()
        except:
            log.exception('send (progress), failed')


class Cancelled:
    """
    A callable added to the Context and used
    by plugin methods to check for cancellation.
    :ivar tracker: The cancellation tracker.
    :type tracker: Tracker
    """

    def __init__(self, sn):
        """
        :param sn: Serial number.
        :type sn: str
        """
        self.sn = sn
        self.tracker = Tracker()

    def __call__(self):
        return self.tracker.cancelled(self.sn)

    def __del__(self):
        self.tracker.remove(self.sn)