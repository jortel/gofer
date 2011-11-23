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

import inspect
from gofer import proxy
from gofer import Singleton
from gofer.messaging import Options
from gofer.rmi.stub import Stub
from threading import RLock


def agent(uuid, **options):
    """
    Get a (mock) proxy for the remote Agent.
    @param uuid: An agent ID.
    @type uuid: str
    @return: A (mock) agent proxy.
    @rtype: L{MockContainer}
    """
    return MockContainer(uuid, None, **options)

def register(**mocks):
    """
    Register (mock) stubs.
    """
    Factory.register(**mocks)
    
def purge():
    """
    Purge (mock) stubs
    """
    Factory.purge()

def install():
    """
    Install the mock agent.
    """
    proxy.Agent = agent
    proxy.agent = agent

def reset():
    """
    Reset (mock) container singletons.
    """
    MockContainer.reset()

def all():
    """
    Get all mock container instances.
    @return: A list of mock container instances.
    @rtype: L{MockContainer}
    """
    return MockContainer.all()
    
    
class MetaContainer(Singleton):
    """
    Mock container singleton by uuid only.
    """

    @classmethod
    def key(cls, t, d):
        if t:
            return t[0]
        else:
            return None


class MockContainer:
    """
    The (mock) stub container
    @ivar __id: The peer ID.
    @type __id: str
    @ivar __options: Container options.
    @type __options: L{Options}
    @ivar __stubs: A cache of stubs.
    @type __stubs: dict
    """
    
    __metaclass__ = MetaContainer
    
    def __init__(self, uuid, producer=None, **options):
        """
        @param uuid: The peer ID.
        @type uuid: str
        @param producer: An AMQP producer (unused).
        @type producer: L{gofer.messaging.producer.Producer}
        @param options: keyword options.
        @type options: dict
        """
        self.__id = uuid
        self.__options = Options()
        self.__options.update(options)
        self.__stubs = {}
    
    def __getattr__(self, name):
        """
        Get a stub by name.
        @param name: The name of a stub class.
        @type name: str
        @return: A stub object.
        @rtype: L{MockStub}
        """
        stub = self.__stubs.get(name)
        if stub is None:
            stub = Factory.stub(name)
            if not stub:
                raise AttributeError(name)
            self.__stubs[name] = stub
        return stub

    def __str__(self):
        return '{%s/%s} opt:%s' % \
            (id(self), 
             self.__id, 
             repr(self.__options))
    
    def __repr__(self):
        return str(self)


class Call:
    """
    Call object.
    @ivar call: The call tuple (args,kwargs)
    @type call: tuple
    """
    
    def __init__(self, call):
        """
        @param call: The call tuple.
        @type call: tuple
        """
        self.call = call
    
    @property
    def args(self):
        """
        Get the call argument list.
        """
        return self.call[0]
    
    @property
    def kwargs(self):
        """
        Get the keyword arguments.
        """
        return self.call[1]
    
    def __getitem__(self, n):
        return self.call[n]
    
    def __iter__(self):
        return iter(self.call)
    
    def __str__(self):
        return str(self.call)
    
    def __repr__(self):
        return repr(self.call)


class Stub:
    """
    Mock stub.
    """
    
    @classmethod
    def __instrumented(cls, inst):
        for m in inspect.getmembers(inst, inspect.ismethod):
            setattr(inst, m[0], Method(m[1]))
        return inst
    
    def __init__(self, stub):
        if inspect.isclass(stub):
            stub = stub()
        self.__inst = self.__instrumented(stub)
    
    def __call__(self, *args, **options):
        return self.__inst
    
    def __getattr__(self, name):
        return getattr(self.__inst, name)
    
    def __str__(self):
        return str(self.__inst)
    
    def __repr__(self):
        return repr(self.__inst)


class Method:
    """
    Method wrapper.
    @ivar __method: The (wrapped) method.
    @type __method: instancemethod
    @ivar __history: The call history
    @type __history: list
    @ivar __mutex: The object mutex
    @type __mutex: RLock 
    """
    
    def __init__(self, method):
        """
        @param method: A (wrapped) method.
        @type method: instancemethod
        """
        self.__method = [method]
        self.__history = []
        self.__mutex = RLock()
        
    def __call__(self, *args, **options):
        self.__lock()
        try:
            call = (args, options)
            self.__history.append(call)
            method = self.pop()
            return method(*args, **options)
        finally:
            self.__unlock()
            
    def push(self, method):
        """
        Push a function, exception to be evaluated on next call.
        @param method: A function/exception
        @type method: function/exception
        """
        self.__lock()
        try:
            self.__method.append(method)
        finally:
            self.__unlock()
            
    def pop(self):
        """
        Pop the next method to be executed.
        It could be an exception in which case, it is raised.
        @return: The next method.
        @rtype: callable
        """
        self.__lock()
        try:
            method = self.__method[0]
            if len(self.__method) > 1:
                method = self.__method.pop()
                if isinstance(method, Exception):
                    raise method
            return method
        finally:
            self.__unlock()
            
    def purge(self):
        """
        Purge the call history.
        """
        self.__lock()
        try:
            self.__history = []
        finally:
            self.__unlock()
            
    def history(self):
        """
        Get the call history.
        @return: A list of L{Call}
        @rtype: list
        """
        self.__lock()
        try:
            history = []
            for h in self.__history:
                history.append(Call(h))
            return history
        finally:
            self.__unlock()

    def __lock(self):
        self.__mutex.acquire()
        
    def __unlock(self):
        self.__mutex.release()


class Factory:
    """
    Stub factory
    @cvar mocks: The registered stubs.
    @type mocks: dict
    """
    
    mocks = {}
    
    @classmethod
    def register(cls, **mocks):
        """
        Register an I{mock} to be used instead of
        creating a real stub.
        """
        cls.mocks.update(mocks)
        
    @classmethod
    def purge(cls):
        """
        purge registered mocks.
        """
        mocks = {}
    
    @classmethod
    def stub(cls, name):
        """
        Get a (mock) stub by name.
        @param name: The stub class (or module) name.
        @type name: str
        @return: A stub instance.
        @rtype: L{Stub}
        """
        stub = cls.mocks.get(name)
        if stub:
            return Stub(stub)
        else:
            return None
