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
from logging import getLogger

from gofer.common import Thread, Local, released
from gofer.rmi.tracker import Tracker
from gofer.rmi.store import Pending, Empty
from gofer.messaging import Document, Producer
from gofer.metrics import Timer, timestamp
from gofer.agent.builtin import Builtin


log = getLogger(__name__)


class Task:
    """
    An RMI task to be scheduled on the plugin thread pool.
    :ivar transaction: A pending transaction.
    :type transaction: Transaction
    :ivar ts: Timestamp
    :type ts: float
    """

    context = Local()

    @staticmethod
    def _producer(plugin):
        """
        Get a configured producer.
        :param plugin: A plugin.
        :type plugin: gofer.agent.plugin.Plugin
        :return: A producer.
        :rtype: Producer
        """
        producer = Producer(plugin.url)
        producer.authenticator = plugin.authenticator
        return producer

    def __init__(self, transaction):
        """
        :param transaction: A pending transaction.
        :type transaction: Transaction
        """
        self.transaction = transaction
        self.producer = None
        self.ts = time()

    @property
    def plugin(self):
        return self.transaction.plugin

    @property
    def request(self):
        return self.transaction.request

    @released
    def __call__(self):
        """
        Dispatch received request.
        """
        request = self.request
        cancelled = Cancelled(request.sn)
        if not self.plugin.url or cancelled():
            self.discard()
            return
        self.context.sn = request.sn
        self.context.progress = Progress(self)
        self.context.cancelled = cancelled
        self.producer = self._producer(self.plugin)
        self.producer.open()
        try:
            self.send_started(request)
            result = self.plugin.dispatch(request)
            self.commit()
            self.send_reply(request, result)
        finally:
            self.context.sn = None
            self.context.progress = None
            self.context.cancelled = None
            self.producer.close()

    def commit(self):
        """
        Commit the transaction.
        """
        self.transaction.commit()

    def discard(self):
        """
        Discard the transaction.
        """
        self.transaction.discard()

    def send_started(self, request):
        """
        Send the a status update if requested.
        :param request: The received request.
        :type request: Document
        """
        sn = request.sn
        data = request.data
        address = request.replyto
        if not address:
            return
        try:
            self.producer.send(
                address,
                sn=sn,
                data=data,
                status='started',
                timestamp=timestamp())
        except Exception:
            log.exception('Send: started, failed')

    def send_reply(self, request, result):
        """
        Send the reply if requested.
        :param request: The received request.
        :type request: Document
        :param result: The request result.
        :type result: object
        """
        sn = request.sn
        data = request.data
        ts = request.ts
        now = time()
        duration = Timer(ts, now)
        address = request.replyto
        log.info('Request: %s processed in: %s', sn, duration)
        if not address:
            return
        try:
            self.producer.send(
                address,
                sn=sn,
                data=data,
                result=result,
                timestamp=timestamp())
        except Exception:
            log.exception('Send: reply, failed: %s', result)


class Transaction(object):
    """
    A request transaction.
    :ivar pending: A pending queue.
    :type pending: Pending
    :ivar request: The subject of the transaction.
    :type request: Document
    """

    def __init__(self, plugin, pending, request):
        """
        :param plugin: A plugin.
        :type plugin: gofer.agent.plugin.Plugin
        :param pending: A pending queue.
        :type pending: Pending
        :param request: An RMI request.
        :type request: Document
        """
        self.plugin = plugin
        self.pending = pending
        self.request = request

    @property
    def id(self):
        return self.request.sn

    def commit(self):
        """
        Commit the transaction.
        The commit is propagated to the pending queue.
        """
        self.pending.commit(self.request.sn)
        log.info('Request: %s, committed', self.id)

    def discard(self):
        """
        Discard the transaction.
        """
        self.pending.commit(self.request.sn)
        log.info('Request: %s, discarded', self.id)


class Scheduler(Thread):
    """
    The pending request scheduler.
    Processes the *pending* queue.
    """

    def __init__(self, plugin):
        """
        :param plugin: A plugin.
        :type plugin: gofer.agent.plugin.Plugin
        """
        Thread.__init__(self, name='scheduler:%s' % plugin.name)
        self.plugin = plugin
        self.pending = Pending(plugin.name)
        self.builtin = Builtin(plugin)
        self.setDaemon(True)

    def run(self):
        """
        Read the pending queue and dispatch requests
        to the plugin thread pool.
        """
        while not Thread.aborted():
            try:
                request = self.pending.get()
            except Empty:
                # aborted
                break
            try:
                plugin = self.select_plugin(request)
                transaction = Transaction(plugin, self.pending, request)
                task = Task(transaction)
                plugin.pool.run(task)
            except Exception:
                self.pending.commit(request.sn)
                log.exception(request.sn)

    def select_plugin(self, request):
        """
        Select the plugin based on the request.
        :param request: A request to be scheduled.
        :rtype request: gofer.messaging.Document
        :return: The appropriate plugin.
        :rtype: gofer.agent.plugin.Plugin
        """
        call = Document(request.request)
        if self.builtin.provides(call.classname):
            plugin = self.builtin
        else:
            plugin = self.plugin
        return plugin

    def add(self, request):
        """
        Add a request to be scheduled.
        :param request: A request to be scheduled.
        :rtype request: gofer.messaging.Document
        """
        self.pending.put(request)

    def shutdown(self):
        """
        Shutdown the scheduler.
        """
        self.builtin.shutdown()
        self.abort()


class Context:
    """
    Remote method invocation context.
    Provides call context to method implementations.
    """

    @staticmethod
    def current():
        return Task.context


class Progress:
    """
    Provides support for progress reporting.
    :ivar task: The current task.
    :type task: Task
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
        self.task = task
        self.total = 0
        self.completed = 0
        self.details = {}

    @property
    def producer(self):
        """
        Get a producer.
        :return: An AMQP producer.
        :rtype: Producer
        """
        return self.task.producer

    def report(self):
        """
        Send the progress report.
        """
        sn = self.task.request.sn
        data = self.task.request.data
        address = self.task.request.replyto
        if not address:
            return
        try:
            self.producer.send(
                address,
                sn=sn,
                data=data,
                status='progress',
                total=self.total,
                completed=self.completed,
                details=self.details)
        except Exception:
            log.exception('Send: progress, failed')


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
        try:
            self.tracker.remove(self.sn)
        except KeyError:
            # already cleaned up
            pass
