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

from threading import RLock


class Singleton(type):
    """
    Singleton metaclass
    usage: __metaclass__ = Singleton
    """

    __inst = {}
    __mutex = RLock()

    @staticmethod
    def reset():
        Singleton.__inst = {}

    @staticmethod
    def key(t, d):
        key = []
        for x in t:
            if isinstance(x, (basestring, int, float, bool)):
                key.append(x)
        for k in sorted(d.keys()):
            v = d[k]
            if isinstance(v, (basestring, int, float, bool)):
                key.append((k, v))
        return repr(key)

    @staticmethod
    def all():
        Singleton.__lock()
        try:
            return Singleton.__inst.values()
        finally:
            Singleton.__unlock()

    def __call__(cls, *args, **kwargs):
        cls.__lock()
        try:
            key = (id(cls), cls.key(args, kwargs))
            inst = cls.__inst.get(key)
            if inst is None:
                inst = type.__call__(cls, *args, **kwargs)
                cls.__inst[key] = inst
            return inst
        finally:
            cls.__unlock()

    @staticmethod
    def __len__():
        Singleton.__lock()
        try:
            return len(Singleton.__inst)
        finally:
            Singleton.__unlock()

    @staticmethod
    def __lock():
        Singleton.__mutex.acquire()

    @staticmethod
    def __unlock():
        Singleton.__mutex.release()


def synchronized(fn):
    """
    Decorator that provides reentrant method invocation
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
        if isinstance(thing, object):
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

