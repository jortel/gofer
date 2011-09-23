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
Provides decorator classes & funcitons.
"""

from gofer import NAME
from gofer.messaging import Options
from gofer.collator import Collator


class Remote:
    """
    @cvar functions: The list of decorated functions.
    """
    functions = []
    
    @classmethod
    def add(cls, fn):
        cls.functions.append(fn)

    @classmethod
    def purge(cls, mod):
        purged = []
        for fn in cls.find(mod):
            purged.append(fn)
        for fn in purged:
            cls.functions.remove(fn)
            
    @classmethod
    def find(cls, mod):
        for fn in cls.functions:
            if fn.__module__ == mod:
                yield fn
                
    @classmethod
    def clear(cls):
        cls.functions = []
    
    @classmethod
    def collated(cls):
        collated = []
        c = Collator()
        classes, functions = c.collate(cls.functions)
        for c in classes.keys():
            collated.append(c)
        for m in functions.keys():
            collated.append(m)
        return collated
    
def __options(fn):
    """
    Ensure funtion has the gofer options attribute
    and return it.
    @param fn: A function
    @return: The funtion options object.
    @rtype: L{Options}
    """
    if not hasattr(fn, NAME):
        opt = Options()
        setattr(fn, NAME, opt)
    else:
        opt = getattr(fn, NAME)
    return opt


def remote(*args, **kwargs):
    """
    Remote method decorator.
    keywords:
      - shared: method shared across plugins.
      - secret: authorization secret.
    """
    shared = bool(kwargs.get('shared', 1))
    secret = kwargs.get('secret',())
    def df(fn):
        opt = __options(fn)
        opt.shared = shared
        opt.secret = secret
        Remote.add(fn)
        return fn
    if args:
        return df(args[0])
    else:
        return df
    
    
def pam(*args, **kwargs):
    """
    PAM authentication method decorator.
    keywords:
      - user: user name.
      - service: (optional) PAM service.
    """
    user = kwargs.get('user')
    service = kwargs.get('service')
    if not user:
        raise Exception('(user) must be specified')
    def df(fn):
        opt = __options(fn)
        opt.pam = Options(user=user, service=service)
        return fn
    if args:
        return df(args[0])
    else:
        return df


def user(*args, **kwargs):
    """
    user (PAM) authentication method decorator.
    keywords:
      - name: user name.
    """
    name = kwargs.get('name')
    return pam(user=name)
