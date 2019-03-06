#
# Copyright (c) 2015 Red Hat, Inc.
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

import os
import errno
import atexit

from copy import copy
from logging import getLogger
from threading import local as _Local
from threading import Thread as _Thread
from threading import current_thread
from threading import Event, RLock

from . import inspection


log = getLogger(__name__)


def mkdir(path):
    """
    Make a directory at the specified path.
    :param path: An absolute path.
    :type path: str
    """
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise


def rmdir(path):
    """
    Delete a directory at the specified path.
    :param path: An absolute path.
    :type path: str
    """
    try:
        os.rmdir(path)
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise


def unlink(path):
    """
    Unlink the specified path.
    :param path: An absolute path.
    :type path: str
    """
    try:
        os.unlink(path)
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise


def nvl(thing, default):
    """
    None value defaulter.
    :param thing: An object.
    :param default: The value when thing is None.
    :return: thing|default
    """
    if thing is None:
        return default
    else:
        return thing


def valid_path(path, mode=os.R_OK):
    """
    Validate the specified path.
    :param path: An absolute file path.
    :type path: sr
    :param mode: A permission mode.  (Eg: os.R_OK).
    :type mode: int
    :raise: ValueError
    """
    if not path:
        return
    if not os.access(path, os.F_OK):
        raise ValueError('"%s" not found' % path)
    if not os.access(path, mode):
        raise ValueError('"%s" insufficient permissions' % path)


def new(T, state=None):
    """
    Build objects.
    :param T: The type of object to build.
    :type T: type|class
    :param state: Optional object state.
    :type state: dict
    :return: The new object.
    """
    if issubclass(T, object):
        inst = T.__new__(T)
        inst.__dict__.update(state or {})
    else:
        import new
        inst = new.instance(T, state)
    return inst


def newT(name, bases=(), state=None):
    """
    Build a new class.
    :param name: The class name.
    :type name: str
    :param bases: Base classes.
    :type bases: tuple
    :param state: Class attributes.
    :type state: dict
    :return: The new class.
    """
    return type(name, bases, state or {})


class Thread(_Thread):
    """
    Thread that supports an abort event.
    """

    ABORT = '__aborted__'

    def __init__(self, *args, **kwargs):
        super(Thread, self).__init__(*args, **kwargs)
        setattr(self, Thread.ABORT, Event())

    def start(self):
        """
        Start the thread.
        """
        def handler():
            self.abort()
            self.join()
        atexit.register(handler)
        super(Thread, self).start()

    @staticmethod
    def current():
        """
        Get the current thread.

        :return: The current thread.
        :rtype: _Thread
        """
        return current_thread()

    @staticmethod
    def aborted():
        """
        Check abort event.
        :return: True if raised.
        :rtype: bool
        """
        thread = Thread.current()
        try:
            event = getattr(thread, Thread.ABORT)
        except AttributeError:
            event = Event()
        aborted = event.isSet()
        if aborted:
            log.debug('thread:%s, ABORTED', thread.getName())
        return aborted

    def abort(self):
        """
        Abort event raised.
        """
        aborted = getattr(self, Thread.ABORT)
        aborted.set()


class Local(object):
    """
    Thread local object.
    Provides an interface whereby attributes can have a default.
    The AttributeError is only raised when the local object does not
    have the attribute set and not default has been specified.
    """

    KEY = 'storage'
    DEFAULT = 'default'

    def __init__(self, **default):
        self.__dict__[Local.KEY] = _Local()
        self.__dict__[Local.DEFAULT] = default

    def __setattr__(self, name, value):
        setattr(self.__dict__[Local.KEY], name, value)

    def __getattr__(self, name):
        try:
            return getattr(self.__dict__[Local.KEY], name)
        except AttributeError as nf:
            d = self.__dict__[Local.DEFAULT].get(name)
            if d is not None:
                d = copy(d)
                setattr(self.__dict__[Local.KEY], name, d)
                return d
            else:
                raise nf


class Singleton(type):
    """
    Singleton metaclass

    usage: class Thing(metaclass=Singleton)
    """

    _inst = {}

    @staticmethod
    def key(args, keywords):
        key = []
        for thing in args:
            if isinstance(thing, (str, int, float, bool)):
                key.append(thing)
        for k in sorted(keywords.keys()):
            v = keywords[k]
            if isinstance(v, (str, int, float, bool)):
                key.append((k, v))
        return repr(key)

    def __call__(cls, *args, **kwargs):
        key = (id(cls), Singleton.key(args, kwargs))
        inst = Singleton._inst.get(key)
        if inst is None:
            inst = type.__call__(cls, *args, **kwargs)
            Singleton._inst[key] = inst
        return inst


class ThreadSingleton(type):
    """
    Thread Singleton metaclass

    usage: class Thing(metaclass=ThreadSingleton)
    """

    _inst = Local(all={})

    @staticmethod
    def all():
        return ThreadSingleton._inst.all

    @staticmethod
    def purge():
        d = ThreadSingleton.all()
        ThreadSingleton._inst.all = {}
        return d.values()

    def __call__(cls, *args, **kwargs):
        _all = ThreadSingleton.all()
        key = (id(cls), Singleton.key(args, kwargs))
        inst = _all.get(key)
        if inst is None:
            inst = type.__call__(cls, *args, **kwargs)
            _all[key] = inst
        return inst


def synchronized(fn):
    """
    Decorator that provides re-entrant method invocation
    using the object's mutex.  The object must have a private
    RLock attribute named __mutex.  Intended only for instance
    methods that have a method body that can be safely mutexed
    in it's entirety to prevent deadlock scenarios.
    """
    def sfn(*args, **kwargs):
        inst = args[0]
        bases = list(inspection.mro(inst.__class__))
        mutex = None
        for cn in [c.__name__ for c in bases]:
            name = '_%s__mutex' % cn
            if hasattr(inst, name):
                mutex = getattr(inst, name)
                break
        if mutex is None:
            raise AttributeError('mutex')
        with mutex:
            return fn(*args, **kwargs)
    return sfn


def conditional(fn):
    """
    Decorator that provides event latched method invocation
    using the object's condition.  The object must have a private
    Condition attribute named __condition.  Intended only for instance
    methods that have a method body that can be safely event latched.
    """
    def sfn(*args, **kwargs):
        inst = args[0]
        bases = list(inspection.mro(inst.__class__))
        condition = None
        for cn in [c.__name__ for c in bases]:
            name = '_%s__condition' % cn
            if hasattr(inst, name):
                condition = getattr(inst, name)
                break
        if condition is None:
            raise AttributeError('condition')
        with condition:
            return fn(*args, **kwargs)
    return sfn


def released(fn):
    """
    Decorator.
    All thread singleton resources released.
    """
    def _fn(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        finally:
            for thing in ThreadSingleton.purge():
                try:
                    thing.close()
                except Exception:
                    pass
    return _fn


class Options(object):
    """
    Provides a dict-like object that also provides
    (.) dot notation accessor.
    """

    def __init__(self, *things, **keywords):
        for thing in things:
            if isinstance(thing, dict):
                self.__dict__.update(thing)
                continue
            if isinstance(thing, Options):
                self.__dict__.update(thing.__dict__)
                continue
            raise ValueError(thing)
        self.__dict__.update(keywords)

    def __getattr__(self, name):
        return self.__dict__.get(name)

    def __getitem__(self, name):
        return self.__dict__[name]

    def __setitem__(self, name, value):
        self.__dict__[name] = value

    def __iadd__(self, thing):
        if isinstance(thing, dict):
            self.__dict__.update(thing)
            return self
        if hasattr(thing, '__dict__'):
            self.__dict__.update(thing.__dict__)
            return self
        raise ValueError(thing)

    def __len__(self):
        return len(self.__dict__)

    def __iter__(self):
        return iter(self.__dict__)

    def __repr__(self):
        return repr(self.__dict__)

    def __str__(self):
        return str(self.__dict__)


class List(object):

    def __init__(self):
        self.__mutex = RLock()
        self._list = []

    @synchronized
    def append(self, thing):
        self._list.append(thing)

    @synchronized
    def insert(self, index, thing):
        self._list.insert(index, thing)

    @synchronized
    def remove(self, thing):
        self._list.remove(thing)

    @synchronized
    def __iter__(self):
        return iter(self._list[:])
