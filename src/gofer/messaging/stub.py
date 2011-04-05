#
# Copyright (c) 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
#

"""
Contains stub classes.
Proxies (stubs) are the I{local} representation of I{remote}
classes on which we invoke methods.
"""

from new import classobj
from gofer.messaging import *
from gofer.messaging.dispatcher import Request
from gofer.messaging.window import Window


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
    @ivar __pid: The peer ID.
    @type __pid: str
    @ivar __options: Stub options.
    @type __options: dict.
    """

    def __init__(self, pid, options):
        """
        @param pid: The peer ID.
        @type pid: str
        @param options: Stub options.
        @type options: dict
        """
        self.__pid = pid
        self.__options = Options(options.items())

    def _send(self, request, options):
        """
        Send the request using the configured request method.
        @param request: An RMI request.
        @type request: str
        """
        opts = Options(self.__options)
        opts.update(options)
        method = self.__options.method
        if isinstance(self.__pid, (list,tuple)):
            return method.broadcast(
                        self.__pid,
                        request,
                        window=opts.window,
                        secret=opts.secret,
                        any=opts.any)
        else:
            return method.send(
                        self.__pid,
                        request,
                        window=opts.window,
                        secret=opts.secret,
                        any=opts.any)

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

    def __call__(self, **options):
        """
        Simulated constructor.
        @param options: keyword options.
        @type options: dict
        @return: self
        @rtype: L{Stub}
        """
        self.__options.update(options)
        return self


class MockStub:
    """
    Mock stub (wrapper).
    Ensures that user defined (registered) stubs
    have gofer stub characteristics.
    """
    
    def __init__(self, stub):
        """
        @param stub: A stub to wrap.
        @type stub: (class|object)
        """
        if callable(stub):
            self.stub = stub()
        else:
            self.stub = stub
        
    def __call__(self, **options):
        """
        Simulated constructor.
        @param options: keyword options.
        @type options: dict
        @return: self
        @rtype: L{MockStub}
        """
        return self
        
    def __getattr__(self, name):
        """
        Passthru to wrapped object.
        @param name: The attribute name.
        @type name: str
        @return: wrapped object attribute.
        """
        return getattr(self.stub, name)


class Factory:
    """
    Stub factory
    @cvar __stubs: The stub overrides.
    @type __stubs: dict
    """
    
    __stubs = {}
    
    @classmethod
    def register(cls, **stubs):
        """
        Register an I{entry} to be used instead of
        creating a real stub.
        """
        cls.__stubs.update(stubs)
    
    @classmethod
    def stub(cls, name, destination, options):
        """
        Get a stub by name.  Seach the __stubs for an override and
        return that if found.  Else, make a new stub object.
        @param name: The stub class (or module) name.
        @type name: str
        @param destination: The AMQP destination
        @type destination: L{Destination}
        @param options: A dict of gofer options
        @param options: L{Options}
        @return: A stub instance.
        @rtype: L{Stub}
        """
        entry = cls.__stubs.get(name)
        if entry:
            stub = MockStub(entry)
        else:
            stub = cls.__mkstub(name, destination, options)
        return stub
    
    @classmethod
    def __mkstub(cls, name, destination, options):
        """
        Get a stub by name.
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
        inst = subclass(destination, options)
        return inst
