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
import inspect
import errno

from threading import local as Local
from threading import Thread as _Thread
from threading import currentThread as current_thread
from threading import Event, RLock
from logging import getLogger

try:
    import simplejson as json
except ImportError:
    import json


log = getLogger(__name__)


def utf8(thing):
    """
    Get a utf-8 representation of an object.
    :param thing: An object.
    :return: A utf-8 representation.
    :rtype: str
    """
    return unicode(thing).encode('utf-8')


def mkdir(path):
    """
    Make a directory at the specified path.
    :param path: An absolute path.
    :type path: str
    """
    try:
        os.makedirs(path)
    except OSError, e:
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
    except OSError, e:
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
    except OSError, e:
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
        # valid paths only
        return
    if not os.access(path, os.F_OK):
        raise ValueError('"%s" not found' % path)
    if not os.access(path, mode):
        raise ValueError('"%s" insufficient permissions' % path)


class Thread(_Thread):
    """
    Thread that supports an abort event.
    """

    ABORT = '__aborted__'

    def __init__(self, *args, **kwargs):
        super(Thread, self).__init__(*args, **kwargs)
        setattr(self, Thread.ABORT, Event())

    @staticmethod
    def aborted():
        """
        Check abort event.
        :return: True if raised.
        :rtype: bool
        """
        thread = current_thread()
        try:
            event = getattr(thread, Thread.ABORT)
        except AttributeError:
            event = Event()
        aborted = event.isSet()
        if aborted:
            log.info('thread:%s, ABORTED', thread.getName())
        return aborted

    def abort(self):
        """
        Abort event raised.
        """
        aborted = getattr(self, Thread.ABORT)
        aborted.set()


class Singleton(type):
    """
    Singleton metaclass
    usage: __metaclass__ = Singleton
    """

    _inst = {}

    @staticmethod
    def key(args, keywords):
        key = []
        for thing in args:
            if isinstance(thing, (basestring, int, float, bool)):
                key.append(thing)
        for k in sorted(keywords.keys()):
            v = keywords[k]
            if isinstance(v, (basestring, int, float, bool)):
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
    usage: __metaclass__ = ThreadSingleton
    """

    _inst = Local()

    @staticmethod
    def all():
        try:
            return ThreadSingleton._inst.d
        except AttributeError:
            d = {}
            ThreadSingleton._inst.d = d
            return d

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
        bases = list(inspect.getmro(inst.__class__))
        mutex = None
        for cn in [c.__name__ for c in bases]:
            name = '_%s__mutex' % cn
            if hasattr(inst, name):
                mutex = getattr(inst, name)
                break
        if mutex is None:
            raise AttributeError('mutex')
        mutex.acquire()
        try:
            return fn(*args, **kwargs)
        finally:
            mutex.release()
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
        bases = list(inspect.getmro(inst.__class__))
        mutex = None
        for cn in [c.__name__ for c in bases]:
            name = '_%s__condition' % cn
            if hasattr(inst, name):
                mutex = getattr(inst, name)
                break
        if mutex is None:
            raise AttributeError('condition')
        mutex.acquire()
        try:
            return fn(*args, **kwargs)
        finally:
            mutex.release()
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
            collection = ThreadSingleton.all()
            for thing in collection.values():
                try:
                    thing.close()
                except Exception:
                    pass
    return _fn


class Options(object):
    """
    Provides a dict-like object that also provides
    (.) dot notation accessors.
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
        return utf8(self.__dict__)

    def __unicode__(self):
        return unicode(self.__dict__)


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
