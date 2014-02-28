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

from logging import getLogger

from gofer.messaging.model import Envelope
from gofer.messaging import Consumer
from gofer.rmi.dispatcher import Reply, Return, RemoteException
from gofer.constants import ACCEPTED, REJECTED, STARTED, PROGRESS


log = getLogger(__name__)


class ReplyConsumer(Consumer):
    """
    A request, reply consumer.
    :ivar listener: An reply listener.
    :type listener: any
    :ivar blacklist: A set of serial numbers to ignore.
    :type blacklist: set
    """

    def __init__(self, queue, url=None, transport=None):
        """
        :param queue: The AMQP node.
        :type queue: gofer.transport.model.Queue
        :param url: The broker URL.
        :type url: str
        :param transport: An AMQP transport.
        :type transport: (str|gofer.transport.Transport)
        """
        Consumer.__init__(self, queue, url=url, transport=transport)
        self.listener = None
        self.blacklist = set()

    def start(self, listener):
        """
        Start processing messages on the queue and
        forward to the listener.
        :param listener: A reply listener.
        :type listener: Listener
        """
        self.listener = listener
        self.blacklist = set()
        Consumer.start(self)

    def dispatch(self, envelope):
        """
        Dispatch received request.
        The serial number of failed requests is added to the blacklist
        help prevent dispatching both failure and success replies.
        :param envelope: The received envelope.
        :type envelope: Envelope
        """
        try:
            reply = Reply(envelope)
            if envelope.sn in self.blacklist:
                # ignored
                return
            if reply.accepted():
                reply = Accepted(envelope)
                reply.notify(self.listener)
                return
            if reply.rejected():
                reply = Rejected(envelope)
                reply.notify(self.listener)
                return
            if reply.started():
                reply = Started(envelope)
                reply.notify(self.listener)
                return
            if reply.progress():
                reply = Progress(envelope)
                reply.notify(self.listener)
                return
            if reply.succeeded():
                self.blacklist.add(envelope.sn)
                reply = Succeeded(envelope)
                reply.notify(self.listener)
                return
            if reply.failed():
                self.blacklist.add(envelope.sn)
                reply = Failed(envelope)
                reply.notify(self.listener)
                return
        except Exception:
            log.exception(envelope)


class AsyncReply:
    """
    Asynchronous request reply.
    :ivar sn: The request serial number.
    :type sn: str
    :ivar origin: Which endpoint sent the reply.
    :type origin: str
    :ivar any: User defined (round-tripped) data.
    :type any: object
    """

    def __init__(self, envelope):
        """
        :param envelope: The received envelope.
        :type envelope: Envelope
        """
        self.sn = envelope.sn
        self.origin = envelope.routing[0]
        self.any = envelope.any

    def notify(self, listener):
        """
        Notify the specified listener.
        :param listener: The listener to notify.
        :type listener: Listener or callable.
        """
        pass

    def __str__(self):
        s = list()
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
        :return: True when succeeded.
        :rtype: bool
        """
        return False

    def failed(self):
        """
        Get whether the reply indicates failure.
        :return: True when failed.
        :rtype: bool
        """
        return not self.succeeded()

    def throw(self):
        """
        Throw contained exception.
        :raise Exception: When contained.
        """
        pass


class Succeeded(FinalReply):
    """
    Successful reply to asynchronous operation.
    :ivar retval: The returned value.
    :type retval: object
    """

    def __init__(self, envelope):
        """
        :param envelope: The received envelope.
        :type envelope: Envelope
        """
        AsyncReply.__init__(self, envelope)
        reply = Return(envelope.result)
        self.retval = reply.retval

    def succeeded(self):
        return True

    def __str__(self):
        s = list()
        s.append(AsyncReply.__str__(self))
        s.append('  retval:')
        s.append(str(self.retval))
        return '\n'.join(s)


class Failed(FinalReply):
    """
    Failed reply to asynchronous operation.  This reply
    indicates an exception was raised.
    :ivar exval: The returned exception.
    :type exval: object
    :see: Failed.throw
    """

    def __init__(self, envelope):
        """
        :param envelope: The received envelope.
        :type envelope: Envelope
        """
        AsyncReply.__init__(self, envelope)
        reply = Return(envelope.result)
        self.exval = RemoteException.instance(reply)
        self.xmodule = reply.xmodule,
        self.xclass = reply.xclass
        self.xstate = reply.xstate
        self.xargs = reply.xargs

    def throw(self):
        raise self.exval

    def __str__(self):
        s = list()
        s.append(AsyncReply.__str__(self))
        s.append('  exval: %s' % str(self.exval))
        s.append('  xmodule: %s' % self.xmodule)
        s.append('  xclass: %s' % self.xclass)
        s.append('  xstate: %s' % self.xstate)
        s.append('  xargs: %s' % self.xargs)
        return '\n'.join(s)


class Accepted(AsyncReply):
    """
    An asynchronous operation accepted.
    :see: Failed.throw
    """

    def notify(self, listener):
        if callable(listener):
            listener(self)
        else:
            listener.accepted(self)

    def __str__(self):
        s = list()
        s.append(AsyncReply.__str__(self))
        s.append(ACCEPTED)
        return '\n'.join(s)


class Rejected(AsyncReply):
    """
    An asynchronous operation rejected.
    :see: Failed.throw
    """

    def notify(self, listener):
        if callable(listener):
            listener(self)
        else:
            listener.rejected(self)

    def __str__(self):
        s = list()
        s.append(AsyncReply.__str__(self))
        s.append(REJECTED)
        return '\n'.join(s)


class Started(AsyncReply):
    """
    An asynchronous operation started.
    :see: Failed.throw
    """

    def notify(self, listener):
        if callable(listener):
            listener(self)
        else:
            listener.started(self)

    def __str__(self):
        s = list()
        s.append(AsyncReply.__str__(self))
        s.append(STARTED)
        return '\n'.join(s)


class Progress(AsyncReply):
    """
    Progress reported for an asynchronous operation.
    :ivar total: The total number of units.
    :type total: int
    :ivar completed: The total number of completed units.
    :type completed: int
    :ivar details: Optional information about the progress.
    :type details: object
    :see: Failed.throw
    """

    def __init__(self, envelope):
        """
        :param envelope: The received envelope.
        :type envelope: Envelope
        """
        AsyncReply.__init__(self, envelope)
        self.total = envelope.total
        self.completed = envelope.completed
        self.details = envelope.details

    def notify(self, listener):
        if callable(listener):
            listener(self)
        else:
            listener.progress(self)

    def __str__(self):
        s = list()
        s.append(AsyncReply.__str__(self))
        s.append('     total: %s' % str(self.total))
        s.append(' completed: %s' % str(self.completed))
        s.append('   details: %s' % str(self.details))
        return '\n'.join(s)


class Listener:
    """
    An asynchronous operation callback listener.
    """

    def succeeded(self, reply):
        """
        Async request succeeded.
        :param reply: The reply data.
        :type reply: Succeeded.
        """
        pass

    def failed(self, reply):
        """
        Async request failed (raised an exception).
        :param reply: The reply data.
        :type reply: Failed.
        """
        pass

    def accepted(self, reply):
        """
        Async request has been accepted.
        :param reply: The request.
        :type reply: Accepted.
        """
        pass

    def rejected(self, reply):
        """
        Async request has been rejected.
        :param reply: The request.
        :type reply: Accepted.
        """
        pass

    def started(self, reply):
        """
        Async request has started.
        :param reply: The request.
        :type reply: Started.
        """
        pass

    def progress(self, reply):
        """
        Async progress report.
        :param reply: The request.
        :type reply: Progress.
        """
        pass
