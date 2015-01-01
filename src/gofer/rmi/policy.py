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

from gofer.messaging import Document, InvalidDocument
from gofer.messaging import Producer, Reader, Queue, Route
from gofer.rmi.dispatcher import Return, RemoteException
from gofer.metrics import Timer


log = getLogger(__name__)


# --- utils ------------------------------------------------------------------


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


# --- exceptions -------------------------------------------------------------


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
        

# --- policy -----------------------------------------------------------------


class RequestMethod:
    """
    Base class for request methods.
    :ivar url: The agent URL.
    :type url: str
    """
    
    def __init__(self, url):
        """
        :param url: The agent URL.
        :type url: str
        """
        self.url = url

    def __call__(self, route, request, **any):
        """
        Send the request.
        :param route: An AMQP route.
        :type route: str
        :param request: A request to send.
        :type request: object
        :keyword any: Any (extra) data.
        """
        raise NotImplementedError()


class Synchronous(RequestMethod):
    """
    The synchronous request method.
    This method blocks until a reply is received.
    """

    def __init__(self, url, options):
        """
        :param url: The agent URL.
        :type url: str
        :param options: Policy options.
        :type options: gofer.messaging.model.Options
        """
        RequestMethod.__init__(self, url)
        self.timeout = Timeout.seconds(options.timeout or 10)
        self.wait = Timeout.seconds(options.wait or 90)
        self.progress = options.progress
        self.authenticator = options.authenticator

    def _get_accepted(self, sn, reader):
        """
        Get the 'accepted' reply matched by serial number.
        In the event the 'accepted' message got lost, the 'started'
        status is also processed.
        :param sn: The request serial number.
        :type sn: str
        :param reader: A reader.
        :type reader: gofer.messaging.consumer.Reader
        :return: The matched reply document.
        :rtype: Document
        """
        document = reader.search(sn, self.timeout)
        if not document:
            raise RequestTimeout(sn, self.timeout)
        if document.status == 'rejected':
            raise InvalidDocument(
                code=document.code,
                document='N/A',
                description='serial=%s' % sn,
                details=document.details)
        if document.status in ('accepted', 'started'):
            log.debug('request (%s), %s', sn, document.status)
        else:
            self._on_reply(document)

    def _get_reply(self, sn, reader):
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
        while True:
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
            if document.status == 'rejected':
                raise InvalidDocument(document.code, sn, document.details)
            if document.status in ('accepted', 'started'):
                continue
            if document.status == 'progress':
                self._on_progress(document)
            else:
                return self._on_reply(document)
        
    def _on_reply(self, document):
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
        
    def _on_progress(self, document):
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
                    any=document.any,
                    total=document.total,
                    completed=document.completed,
                    details=document.details)
                reporter(report)
        except Exception:
            log.error('progress callback failed', exc_info=1)

    def __call__(self, route, request, **any):
        """
        Send the request then read the reply.
        :param route: An AMQP route.
        :type route: str
        :param request: A request to send.
        :type request: object
        :keyword any: Any (extra) data.
        :return: The result of the request.
        :rtype: object
        :raise Exception: returned by the peer.
        """
        reply = Route(route)
        reply.queue = Queue(str(uuid4()))
        reply.queue.durable = False
        reply.queue.auto_delete = True
        reply.declare(self.url)
        producer = Producer(self.url)
        producer.authenticator = self.authenticator
        producer.open()
        try:
            sn = producer.send(
                route,
                ttl=self.timeout,
                replyto=str(reply),
                request=request,
                **any)
        finally:
            producer.close()
        log.debug('sent (%s): %s', route, request)
        reader = Reader(reply.queue, self.url)
        reader.authenticator = self.authenticator
        reader.open()
        try:
            self._get_accepted(sn, reader)
            return self._get_reply(sn, reader)
        finally:
            reader.close()


class Asynchronous(RequestMethod):
    """
    The asynchronous request method.
    """

    def __init__(self, url, options):
        """
        :param url: The agent URL.
        :type url: str
        :param options: Policy options.
        :type options: gofer.messaging.model.Options
        """
        RequestMethod.__init__(self, url)
        self.reply = options.reply
        self.timeout = Timeout.seconds(options.timeout)
        self.trigger = options.trigger
        self.authenticator = options.authenticator

    def __call__(self, route, request, **any):
        """
        Send the specified request and redirect the reply to the
        queue for the specified reply *correlation* tag.
        A trigger(1) specifies a *manual* trigger.
        :param route: An AMQP route.
        :type route: route
        :param request: A request to send.
        :type request: object
        :keyword any: Any (extra) data.
        :return: The request serial number.
        :rtype: str
        """
        trigger = Trigger(self, route, request, any)
        if self.trigger == 1:
            return trigger
        trigger()
        return trigger.sn


class Trigger:
    """
    Asynchronous trigger.
    :ivar _pending: pending flag.
    :type _pending: bool
    :ivar _sn: serial number
    :type _sn: str
    :ivar _policy: The policy object.
    :type _policy: Asynchronous
    :ivar _route: An AMQP route.
    :type _route: str
    :ivar _request: A request to send.
    :type _request: object
    :ivar _any: Any (extra) data.
    :type _any: dict
    """

    def __init__(self, policy, route, request, any):
        """
        :param policy: The policy object.
        :type policy: Asynchronous
        :param route: An AMQP route.
        :type route: str
        :param request: A request to send.
        :type request: object
        :keyword any: Any (extra) data.
        """
        self._pending = True
        self._sn = str(uuid4())
        self._policy = policy
        self._route = route
        self._request = request
        self._any = any
        
    @property
    def sn(self):
        """
        Get serial number.
        :return: The request serial number.
        :rtype: str
        """
        return self._sn
        
    def _send(self):
        """
        Send the request using the specified policy
        object and generated serial number.
        """
        policy = self._policy
        route = self._route
        request = self._request
        any = self._any
        producer = Producer(policy.url)
        producer.authenticator = policy.authenticator
        producer.open()
        try:
            producer.send(
                route,
                sn=self._sn,
                ttl=policy.timeout,
                replyto=policy.reply,
                request=request,
                **any)
        finally:
            producer.close()
        log.debug('sent (%s): %s', route, request)

    def __call__(self):
        if self._pending:
            self._send()
            self._pending = False
        else:
            raise Exception('trigger already executed')

    def __str__(self):
        return self._sn
