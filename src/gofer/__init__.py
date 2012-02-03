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

from threading import RLock


# process name used to build the following paths:
#   /etc/<NAME>
#   /etc/<NAME>/agent.conf
#   /etc/<NAME>/conf.d
#   /etc/<NAME>/plugins
#   /var/lib/<NAME>
#   /var/lib/<NAME>/messaging
#   /var/lib/<NAME>/journal
#   /usr/lib/<NAME>/<plugin>
#   /var/run/<NAME>d.pid
#   /var/log/<NAME>/agent.log
#   ~/.<NAME>/agent.conf
NAME = 'gofer'


class Singleton(type):
    """
    Singleton metaclass
    usage: __metaclass__ = Singleton
    """
    
    __inst = {}
    __mutex = RLock()

    @classmethod
    def reset(cls):
        cls.__inst = {}
            
    @classmethod
    def key(cls, t, d):
        key = []
        for x in t:
            if isinstance(x, (str,int,float)):
                key.append(x)
        for k in sorted(d.keys()):
            v = d[k]
            if isinstance(v, (str,int,float)):
                key.append((k,v))
        return repr(key)
    
    @classmethod   
    def all(cls):
        cls.__lock()
        try:
            return cls.__inst.values()
        finally:
            cls.__unlock()
    
    def __call__(cls, *args, **kwargs):
        cls.__lock()
        try:
            key = (cls.__name__,
                   cls.key(args, kwargs))
            inst = cls.__inst.get(key)
            if inst is None: 
                inst = type.__call__(cls, *args, **kwargs)
                cls.__inst[key] = inst
            return inst
        finally:
            cls.__unlock()
    
    @classmethod   
    def __len__(cls):
        cls.__lock()
        try:
            return len(cls.__inst)
        finally:
            cls.__unlock()

    @classmethod
    def __lock(cls):
        cls.__mutex.acquire()

    @classmethod
    def __unlock(cls):
        cls.__mutex.release()


def synchronized(fn):
    """
    Decorator that provides reentrant method invocation
    using the object's mutex.  The object must have a private
    RLock attribute named __mutex.  Intended only for instance
    methods that have a method body that can be safely mutexed
    in it's entirety to prevent deadlock senarios.
    """
    def sfn(*args, **kwargs):
        inst = args[0]
        cn = inst.__class__.__name__
        mutex = getattr(inst, '_%s__mutex' % cn)
        mutex.acquire()
        try:
            return fn(*args, **kwargs)
        finally:
            mutex.release()
    return sfn