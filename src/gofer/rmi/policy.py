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

from gofer.messaging.model import Document, InvalidDocument, getuuid
from gofer.messaging import Destination
from gofer.rmi.dispatcher import Return, RemoteException
from gofer.transport import Transport
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
    :ivar transport: The AMQP transport.
    :type transport: str
    """
    
    def __init__(self, url, transport):
        """
        :param url: The agent URL.
        :type url: str
        :param transport: The AMQP transport.
        :type transport: str
        """
        self.url = url
        self.transport = transport

    def send(self, destination, request, **any):
        """
        Send the request..
        :param destination: An AMQP destination.
        :type destination: gofer.transport.model.Destination
        :param request: A request to send.
        :type request: object
        :keyword any: Any (extra) data.
        """
        pass

    def broadcast(self, addresses, request, **any):
        """
        Broadcast the request.
        :param addresses: A list of destination AMQP queues.
        :type addresses: [gofer.transport.node.Destination,..]
        :param request: A request to send.
        :type request: object
        :keyword any: Any (extra) data.
        """
        pass


class Synchronous(RequestMethod):
    """
    The synchronous request method.
    This method blocks until a reply is received.
    :ivar queue: An AMQP queue.
    :type queue: gofer.transport.model.Queue
    """

    def __init__(self, url, transport, options):
        """
        :param url: The agent URL.
        :type url: str
        :param transport: The AMQP transport.
        :type transport: str
        :param options: Policy options.
        :type options: dict
        """
        tp = Transport(transport)
        RequestMethod.__init__(self, url, transport)
        self.timeout = Timeout.seconds(options.timeout or 10)
        self.wait = Timeout.seconds(options.wait or 90)
        self.progress = options.progress
        self.queue = tp.queue(getuuid())
        self.authenticator = options.authenticator
        self.queue.auto_delete = True
        self.queue.declare(self.url)

    def send(self, destination, request, **any):
        """
        Send the request then read the reply.
        :param destination: An AMQP destination.
        :type destination: gofer.transport.model.Destination
        :param request: A request to send.
        :type request: object
        :keyword any: Any (extra) data.
        :return: The result of the request.
        :rtype: object
        :raise Exception: returned by the peer.
        """
        tp = Transport(self.transport)
        replyto = self.queue.destination()
        producer = tp.producer(url=self.url)
        producer.authenticator = self.authenticator
        queue = tp.queue(destination.routing_key)
        queue.declare(self.url)
        try:
            sn = producer.send(
                destination,
                ttl=self.timeout,
                replyto=replyto.dict(),
                request=request,
                **any)
        finally:
            producer.close()
        log.debug('sent (%s): %s', repr(destination), request)
        reader = tp.reader(self.url, self.queue)
        reader.authenticator = self.authenticator
        try:
            self.__get_accepted(sn, reader)
            return self.__get_reply(sn, reader)
        finally:
            reader.close()

    def __get_accepted(self, sn, reader):
        """
        Get the 'accepted' reply matched by serial number.
        In the event the 'accepted' message got lost, the 'started'
        status is also processed.
        :param sn: The request serial number.
        :type sn: str
        :param reader: A reader.
        :type reader: gofer.messaging.factory.Reader
        :return: The matched reply document.
        :rtype: Document
        """
        document = reader.search(sn, self.timeout)
        if not document:
            raise RequestTimeout(sn, self.timeout)
        if document.status == 'rejected':
            raise InvalidDocument(document.code, sn, document.details)
        if document.status in ('accepted', 'started'):
            log.debug('request (%s), %s', sn, document.status)
        else:
            self.__on_reply(document)

    def __get_reply(self, sn, reader):
        """
        Get the reply matched by serial number.
        :param sn: The request serial number.
        :type sn: str
        :param reader: A reader.
        :type reader: gofer.messaging.factory.Reader
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
                self.__on_progress(document)
            else:
                return self.__on_reply(document)
        
    def __on_reply(self, document):
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
        
    def __on_progress(self, document):
        """
        Handle the progress report.
        :param document: The status document.
        :type document: Document
        """
        try:
            callback = self.progress
            if callable(callback):
                report = dict(
                    sn=document.sn,
                    any=document.any,
                    total=document.total,
                    completed=document.completed,
                    details=document.details)
                callback(report)
        except:
            log.error('progress callback failed', exc_info=1)


class Asynchronous(RequestMethod):
    """
    The asynchronous request method.
    """

    def __init__(self, url, transport, options):
        """
        :param url: The agent URL.
        :type url: str
        :param transport: The AMQP transport.
        :type transport: str
        :param options: Policy options.
        :type options: dict
        """
        RequestMethod.__init__(self, url, transport)
        self.ctag = options.ctag
        self.timeout = Timeout.seconds(options.timeout)
        self.trigger = options.trigger
        self.authenticator = options.authenticator

    def send(self, destination, request, **any):
        """
        Send the specified request and redirect the reply to the
        queue for the specified reply *correlation* tag.
        A trigger(1) specifies a *manual* trigger.
        :param destination: An AMQP destination.
        :type destination: gofer.transport.model.Destination
        :param request: A request to send.
        :type request: object
        :keyword any: Any (extra) data.
        :return: The request serial number.
        :rtype: str
        """
        trigger = Trigger(self, destination, request, any)
        if self.trigger == 1:
            return trigger
        trigger()
        return trigger.sn

    def broadcast(self, destinations, request, **any):
        """
        Send the specified request and redirect the reply to the
        queue for the specified reply *correlation* tag.
        A trigger(1) specifies a *manual* trigger.
        :param destinations: A list of destinations.
        :type destinations: [gofer.transport.model.Destination,..]
        :param request: A request to send.
        :type request: object
        :keyword any: Any (extra) data.
        """
        triggers = []
        for destination in destinations:
            t = Trigger(self, destination, request, any)
            triggers.append(t)
        if self.trigger == 1:
            return triggers
        for trigger in triggers:
            trigger()
        return [t.sn for t in triggers]

    def replyto(self):
        """
        Get replyto based on the correlation tag.
        The ctag can be a string or a Destination object.
        :return: The replyto AMQP destination.
        :rtype: dict
        """
        if isinstance(self.ctag, str):
            d = Destination(self.ctag)
            return d.dict()
        if isinstance(self.ctag, Destination):
            d = self.ctag
            return d.dict()


class Trigger:
    """
    Asynchronous trigger.
    :ivar __pending: pending flag.
    :type __pending: bool
    :ivar __sn: serial number
    :type __sn: str
    :ivar __policy: The policy object.
    :type __policy: Asynchronous
    :ivar __destination: An AMQP destination.
    :type __destination: gofer.transport.model.Destination
    :ivar __request: A request to send.
    :type __request: object
    :ivar __any: Any (extra) data.
    :type __any: dict
    """

    def __init__(self, policy, destination, request, any):
        """
        :param policy: The policy object.
        :type policy: Asynchronous
        :param destination: An AMQP destination.
        :type destination: gofer.transport.model.Destination
        :param request: A request to send.
        :type request: object
        :keyword any: Any (extra) data.
        """
        self.__pending = True
        self.__sn = getuuid()
        self.__policy = policy
        self.__destination = destination
        self.__request = request
        self.__any = any
        
    @property
    def sn(self):
        """
        Get serial number.
        :return: The request serial number.
        :rtype: str
        """
        return self.__sn
        
    def __send(self):
        """
        Send the request using the specified policy
        object and generated serial number.
        """
        policy = self.__policy
        tp = Transport(policy.transport)
        destination = self.__destination
        replyto = policy.replyto()
        request = self.__request
        any = self.__any
        producer = tp.producer(url=policy.url)
        producer.authenticator = policy.authenticator
        queue = tp.queue(destination.routing_key)
        queue.declare(policy.url)
        try:
            producer.send(
                destination,
                sn=self.__sn,
                ttl=policy.timeout,
                replyto=replyto,
                request=request,
                **any)
        finally:
            producer.close()
        log.debug('sent (%s): %s', repr(destination), request)
    
    def __str__(self):
        return self.__sn
    
    def __call__(self):
        if self.__pending:
            self.__send()
            self.__pending = False
        else:
            raise Exception('trigger already executed')
