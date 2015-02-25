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
Contains request delivery policies.
"""

from logging import getLogger
from uuid import uuid4

from gofer.common import Thread, Options, nvl
from gofer.messaging import Document, InvalidDocument
from gofer.messaging import Producer, Reader, Queue, Exchange
from gofer.rmi.dispatcher import Return, RemoteException
from gofer.metrics import Timer


log = getLogger(__name__)


class Timeout:
    """
    Policy timeout.
    :cvar MINUTE: Minutes in seconds.
    :cvar HOUR: Hour is seconds
    :cvar DAY: Day in seconds
    :cvar SUFFIX: Suffix to multiplier mapping.
    """

    SECOND = 1
    MINUTE = 60
    HOUR = (MINUTE * 60)
    DAY = (HOUR * 24)

    SUFFIX = {
        's': SECOND,
        'm': MINUTE,
        'h': HOUR,
        'd': DAY,
    }

    @classmethod
    def seconds(cls, thing):
        """
        Convert tm to seconds based on suffix.
        :param thing: A timeout value.
            The string value may have a suffix of:
              (s) = seconds
              (m) = minutes
              (h) = hours
              (d) = days
        :type thing: (None|int|float|str)

        """
        if thing is None:
            return thing
        if isinstance(thing, int):
            return thing
        if isinstance(thing, float):
            return int(thing)
        if not isinstance(thing, basestring):
            raise TypeError(thing)
        if not len(thing):
            raise ValueError(thing)
        if cls.has_suffix(thing):
            multiplier = cls.SUFFIX[thing[-1]]
            return multiplier * int(thing[:-1])
        else:
            return int(thing)

    @classmethod
    def has_suffix(cls, tm):
        for k in cls.SUFFIX.keys():
            if tm.endswith(k):
                return True
        return False

    def __init__(self, start=None, duration=None):
        self.start = self.seconds(start)
        self.duration = self.seconds(duration)

    def tuple(self):
        return self.start, self.duration


class RequestTimeout(Exception):
    """
    Request timeout.
    """

    def __init__(self, sn, timeout):
        """
        :param sn: The request serial number.
        :type sn: str
        """
        Exception.__init__(self, sn, timeout)
        
    def sn(self):
        return self.args[0]
    
    def timeout(self):
        return self.args[1]


class Policy(object):
    """
    The method invocation policy.
    :ivar url: The broker URL.
    :type url: str
    :ivar address: The AMQP address.
    :type address: str
    :ivar options: The RMI options.
    :type options: gofer.Options
    """

    def __init__(self, url, address, options):
        """
        :param url: The broker URL.
        :type url: str
        :param address: The AMQP address.
        :type address: str
        :param options: The RMI options.
        :type options: gofer.Options
        """
        self.url = url
        self.address = address
        self.options = options

    @property
    def ttl(self):
        if self.options.ttl:
            return Timeout.seconds(self.options.ttl)
        else:
            return None

    @property
    def wait(self):
        return Timeout.seconds(nvl(self.options.wait, 90))

    @property
    def progress(self):
        return self.options.progress

    @property
    def authenticator(self):
        return self.options.authenticator

    @property
    def reply(self):
        return self.options.reply

    @property
    def trigger(self):
        return self.options.trigger or 0

    @property
    def pam(self):
        if self.options.user:
            return Options(user=self.options.user, password=self.options.password)
        else:
            return None

    @property
    def secret(self):
        return self.options.secret

    @property
    def data(self):
        return self.options.data

    @property
    def exchange(self):
        return self.options.exchange

    def get_reply(self, sn, reader):
        """
        Get the reply matched by serial number.
        :param sn: The request serial number.
        :type sn: str
        :param reader: A reader.
        :type reader: gofer.messaging.consumer.Reader
        :return: The matched reply document.
        :rtype: Document
        """
        timer = Timer()
        timeout = float(self.wait)

        while not Thread.aborted():
            timer.start()
            document = reader.search(sn, int(timeout))
            timer.stop()
            elapsed = timer.duration()
            if elapsed > timeout:
                raise RequestTimeout(sn, self.wait)
            else:
                timeout -= elapsed

            if not document:
                raise RequestTimeout(sn, self.wait)

            # rejected
            if document.status == 'rejected':
                raise InvalidDocument(
                    document.code,
                    document.description,
                    document.document,
                    document.details)

            # accepted | started
            if document.status in ('accepted', 'started'):
                continue

            # progress reported
            if document.status == 'progress':
                self.on_progress(document)
                continue

            # reply
            return self.on_reply(document)
        
    def on_reply(self, document):
        """
        Handle the reply.
        :param document: The reply document.
        :type document: Document
        :return: The matched reply document.
        :rtype: Document
        """
        reply = Return(document.result)
        if reply.succeeded():
            return reply.retval
        else:
            raise RemoteException.instance(reply)
        
    def on_progress(self, document):
        """
        Handle the progress report.
        :param document: The status document.
        :type document: Document
        """
        try:
            reporter = self.progress
            if callable(reporter):
                report = dict(
                    sn=document.sn,
                    data=document.data,
                    total=document.total,
                    completed=document.completed,
                    details=document.details)
                reporter(report)
        except Exception:
            log.error('progress callback failed', exc_info=1)

    def __call__(self, request):
        """
        Send the request then read the reply.
        :param request: A request to send.
        :type request: object
        :rtype: object
        :raise Exception: returned by the peer.
        """
        trigger = Trigger(self, request)
        if self.trigger == Trigger.MANUAL:
            return trigger
        else:
            return trigger()


class Trigger:
    """
    Asynchronous trigger.
    :ivar _pending: pending flag.
    :type _pending: bool
    :ivar _sn: request serial number
    :type _sn: str
    :ivar _policy: The policy object.
    :type _policy: Policy
    :ivar _request: A request to send.
    :type _request: object
    """

    MANUAL = 1  # trigger
    NOWAIT = 0  # wait (seconds)

    def __init__(self, policy, request):
        """
        :param policy: The policy object.
        :type policy: Policy
        :param request: A request to send.
        :type request: object
        """
        self._sn = str(uuid4())
        self._policy = policy
        self._request = request
        self._pending = True

    @property
    def sn(self):
        return self._sn

    def _send(self, reply=None, queue=None):
        """
        Send the request using the specified policy
        object and generated serial number.
        :param reply: The AMQP reply address.
        :type reply: str
        :param queue: The reply queue for synchronous calls.
        :type queue: Queue
        """
        producer = Producer(self._policy.url)
        producer.authenticator = self._policy.authenticator
        producer.open()

        try:
            producer.send(
                self._policy.address,
                self._policy.ttl,
                # body
                sn=self.sn,
                replyto=reply,
                request=self._request,
                secret=self._policy.secret,
                pam=self._policy.pam,
                data=self._policy.data)
        finally:
            producer.close()

        log.debug('sent (%s): %s', self._policy.address, self._request)

        if queue is None:
            # no reply expected
            return self._sn

        reader = Reader(queue, self._policy.url)
        reader.authenticator = self._policy.authenticator
        reader.open()

        try:
            policy = self._policy
            return policy.get_reply(self.sn, reader)
        finally:
            reader.close()

    def __call__(self):
        """
        Trigger pulled.
        Execute the request.
        """
        if not self._pending:
            raise Exception('trigger already executed')
        self._pending = False

        # asynchronous
        if self._policy.reply:
            return self._send(reply=self._policy.reply)
        if self._policy.wait == Trigger.NOWAIT:
            return self._send()

        # synchronous
        queue = Queue()
        queue.durable = False
        queue.declare(self._policy.url)
        reply = queue.name

        if self._policy.exchange:
            exchange = Exchange(self._policy.exchange)
            exchange.bind(queue, self._policy.url)
            reply = '/'.join((self._policy.exchange, queue.name))

        try:
            return self._send(reply=reply, queue=queue)
        finally:
            queue.purge(self._policy.url)
            queue.delete(self._policy.url)

    def __str__(self):
        return self._sn
