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
Contains stub classes.
Proxies (stubs) are the I{local} representation of I{remote}
classes on which we invoke methods.
"""

from new import classobj
from threading import RLock
from gofer.messaging import *
from gofer.rmi.policy import *
from gofer.rmi.dispatcher import Request
from gofer.rmi.window import Window


class Method:
    """
    A dynamic method object used to wrap the RMI call.
    @ivar classname: The target class name.
    @type classname: str
    @ivar name: The target method name.
    @type name: str
    @ivar stub: The stub object used to send the AMQP message.
    @type stub: L{Stub}
    """

    def __init__(self, classname, name, stub):
        """
        @param classname: The target class name.
        @type classname: str
        @param name: The target method name.
        @type name: str
        @param stub: The stub object used to send the AMQP message.
        @type stub: L{Stub}
        """
        self.classname = classname
        self.name = name
        self.stub = stub

    def __call__(self, *args, **kws):
        """
        Invoke the method .
        @param args: The args.
        @type args: list
        @param kws: The I{keyword} arguments.
        @type kws: dict
        """
        opts = Options()
        for k,v in kws.items():
            if k in ('window', 'any',):
                opts[k] = v
                del kws[k]
        request = Request(
            classname=self.classname,
            method=self.name,
            args=args,
            kws=kws)
        return self.stub._send(request, opts)


class Stub:
    """
    The stub class for remote objects.
    @ivar __producer: An AMQP producer.
    @type __producer: L{gofer.messaging.producer.Producer}
    @ivar __destination: The AMQP destination
    @type __destination: L{Destination}
    @ivar __options: Stub options.
    @type __options: L{Options}
    @ivar __mutex: The object mutex.
    @type __mutex: RLock
    @ivar __policy: The invocation policy.
    @type __policy: L{Policy}
    """
    
    @classmethod
    def stub(cls, name, producer, destination, options):
        """
        Factory method.
        @param name: The stub class (or module) name.
        @type name: str
        @param destination: The AMQP destination
        @type destination: L{Destination}
        @param options: A dict of gofer options
        @param options: L{Options}
        @return: A stub instance.
        @rtype: L{Stub}
        """
        subclass = classobj(name, (Stub,), {})
        inst = subclass(producer, destination, options)
        return inst

    def __init__(self, producer, destination, options):
        """
        @param producer: An AMQP producer.
        @type producer: L{gofer.messaging.producer.Producer}
        @param destination: The AMQP destination
        @type destination: L{Destination}
        @param options: Stub options.
        @type options: L{Options}
        """
        self.__producer = producer
        self.__destination = destination
        self.__options = Options(options.items())
        self.__called = (0, None)
        self.__mutex = RLock()
        self.__policy = None

    def _send(self, request, options):
        """
        Send the request using the configured request method.
        @param request: An RMI request.
        @type request: str
        @param options: Invocation options.
        @type options: L{Options}
        """
        self.__lock()
        try:
            return self.__send(request, options)
        finally:
            self.__unlock()
            
    def __send(self, request, options):
        """
        Send the request using the configured request method.
        @param request: An RMI request.
        @type request: str
        @param options: Invocation options.
        @type options: L{Options}
        """
        opts = Options(self.__options)
        opts.update(options)
        request.cntr = self.__called[1]
        policy = self.__getpolicy()
        if isinstance(self.__destination, (list,tuple)):
            return policy.broadcast(
                        self.__destination,
                        request,
                        window=opts.window,
                        secret=opts.secret,
                        pam=self.__getpam(opts),
                        any=opts.any)
        else:
            return policy.send(
                        self.__destination,
                        request,
                        window=opts.window,
                        secret=opts.secret,
                        pam=self.__getpam(opts),
                        any=opts.any)
            
    def __getpam(self, opts):
        """
        Get PAM options.
        @param opts: options dict.
        @type opts: dict
        @return: pam options
        @rtype: L{Options}
        """
        user = opts.user
        if opts.user:
            return Options(
                user=opts.user,
                password=opts.password)
        return None

    def __getattr__(self, name):
        """
        Python vodo.
        Get a I{Method} object for any requested attribte.
        @param name: The attribute name.
        @type name: str
        @return: A method object.
        @rtype: L{Method}
        """
        cn = self.__class__.__name__
        return Method(cn, name, self)

    def __call__(self, *args, **options):
        """
        Simulated constructor.
        The 1st call updates stub options.
        The 2nd call updates remote object constructor
        parameters which are passed on RMI calls.
        @param options: keyword options.
        @type options: dict
        @return: self
        @rtype: L{Stub}
        """
        if not self.__called[0]:
            self.__called = (1, None)
            self.__options.update(options)
        else:
            n = self.__called[0]
            self.__called = (n+1, (args, options))
        return self

    def __getpolicy(self):
        """
        Get the request policy based on options.
        The policy is cached for performance.
        @return: The request policy.
        @rtype: L{Policy}
        """
        if self.__policy is None:
            self.__setpolicy()
        return self.__policy
    
    def __setpolicy(self):
        """
        Set the request policy based on options.
        """
        if self.__async():
            self.__policy = \
                Asynchronous(self.__producer, self.__options)
        else:
            self.__policy = \
                Synchronous(self.__producer, self.__options)

    def __async(self):
        """
        Get whether an I{asynchronous} request method
        should be used based on selected options.
        @return: True if async.
        @rtype: bool
        """
        if ( self.__options.ctag or
             self.__options.async ):
            return True
        return isinstance(self.__destination, (list,tuple))
    
    def __lock(self):
        self.__mutex.acquire()
        
    def __unlock(self):
        self.__mutex.release()
