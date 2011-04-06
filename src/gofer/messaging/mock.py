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


from gofer import Singleton
from gofer.messaging import Options
from gofer.messaging.stub import Stub
from threading import RLock


def history():
    """
    Get (mock) call history object
    """
    return History()

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
    @param mocks: <name>:<mock>
    """
    from gofer import proxy
    proxy.Agent = MockAgent


class History:
    """
    Mock call history 
    """
    
    __metaclass__ = Singleton
    __mutex = RLock()
    
    def __init__(self):
        """
        @ivar stubs: A dict of mock stubs by uuid.
        @type stubs: dict
        """
        self.stubs = {}
    
    def add(self, uuid, stub):
        """
        Add a stub for tracking.
        @param uuid: A uuid.
        @type uuid: str
        @param stub: A stub to be tracked.
        @type stub: L{MockStub}
        """
        self.__lock()
        try:
            calls = self.calls(uuid)
            try:
                calls.append(stub().__history__)
            except:
                pass
        finally:
            self.__unlock()
        
    def purge(self, uuids=()):
        """
        Purge statistics.
        @param uuids: A list of uuids to purge.
            Empty list purges ALL.
        @type uuids: list
        """
        self.__lock()
        try:
            if not uuids:
                self.stubs = {}
            for uuid in uuids:
                try:
                    del self.stubs[uuid]
                except:
                    pass
        finally:
            self.__unlock()

    def calls(self, uuid):
        """
        Get call statistics.
        @param uuid: A uuid filter.
        @type uuid: str
        @return: A list of call tuples
            (method, *arg, **kwargs)
        @rtype: tuple
        """
        self.__lock()
        try:
            calls = self.stubs.get(uuid)
            if calls is None:
                calls = []
                self.stubs[uuid] = calls
            return calls
        finally:
            self.__unlock()
    
    def __lock(self):
        self.__mutex.acquire()
    
    def __unlock(self):
        self.__mutex.release()


class MockContainer:
    """
    The (mock) stub container
    @ivar __id: The peer ID.
    @type __id: str
    @ivar __options: Container options.
    @type __options: L{Options}
    """
    
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
        self.__history = History()
    
    def __getattr__(self, name):
        """
        Get a stub by name.
        @param name: The name of a stub class.
        @type name: str
        @return: A stub object.
        @rtype: L{MockStub}
        """
        stub = Factory.mock(name)
        self.__history.add(self.__id, stub)
        return stub 

    def __str__(self):
        return '{%s} opt:%s' % (self.__id, str(self.__options))
    
    def __repr__(self):
        return str(self)
    
    
class MockStub:
    """
    Mock stub object.
    @ivar __name: The stub (class) name.
    @type __name: str
    @ivar __history__: The call history.
    @type __history__: list
    """
    
    def __init__(self, name):
        """
        @param __name: The stub (class) name.
        @type __name: str
        """
        self.__name = name
        self.__history__ = []
    
    def __getattr__(self, name):
        if name.startswith('__') and name.endswith('__'):
            builtin = self.__dict__.get(name)
            if builtin is None:
                raise AttributeError(name)
            return builtin
        def fn(*A,**K):
            call = (name, A, K)
            self.__history__.append(call)
            return call
        return fn
    
    def __str__(self):
        s = []
        s.append(self.__name)
        s.append(': ')
        s.append(str(self.__history__))
        return ''.join(s)
    
    def __repr__(self):
        return str(self)
    
    def __nonzero__(self):
        return True


class MockClass:
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
            self.__stub = stub()
        else:
            self.__stub = stub
        
    def __call__(self, **options):
        """
        Simulated constructor.
        @param options: keyword options.
        @type options: dict
        @return: self
        @rtype: L{MockClass}
        """
        return self.__stub
        
    def __getattr__(self, name):
        """
        Passthru to wrapped object.
        @param name: The attribute name.
        @type name: str
        @return: wrapped object attribute.
        """
        return getattr(self.__stub, name)

    def __str__(self):
        return str(self.__stub.__class__)
    
    def __repr__(self):
        return str(self)


class Factory:
    """
    Stub factory
    @cvar __mocks: The stub overrides.
    @type __mocks: dict
    """
    
    __mocks = {}
    
    @classmethod
    def register(cls, **mocks):
        """
        Register an I{mock} to be used instead of
        creating a real stub.
        """
        cls.__mocks.update(mocks)
        
    @classmethod
    def purge(cls):
        """
        purge registered mocks.
        """
        __mocks = {}
    
    @classmethod
    def stub(cls, name):
        """
        Get a (mock) stub by name.
        @param name: The stub class (or module) name.
        @type name: str
        @return: A stub instance.
        @rtype: L{Stub}
        """
        mock = cls.__mocks.get(name)
        if mock:
            return MockClass(mock)
        else:
            return None
    
    @classmethod
    def mock(cls, name):
        """
        Get a (mock) stub by name.  If none registered, a
        MockStub is created and returned.
        @param name: The stub class (or module) name.
        @type name: str
        @return: A stub instance.
        @rtype: L{MockClass}
        """
        mock = cls.__mocks.get(name)
        if not mock:
            mock = MockStub(name)
        return MockClass(mock)


class MockAgent(MockContainer):
    """
    A (mock) proxy for the remote Agent.
    """
    pass