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
from gofer.messaging.model import Options
from gofer.collator import Collator


class Remote:
    """
    :cvar functions: The list of decorated functions.
    """
    functions = []
    
    @staticmethod
    def add(fn):
        Remote.functions.append(fn)

    @staticmethod
    def purge(mod):
        purged = []
        for fn in Remote.find(mod):
            purged.append(fn)
        for fn in purged:
            Remote.functions.remove(fn)
            
    @staticmethod
    def find(mod):
        for fn in Remote.functions:
            if fn.__module__ == mod:
                yield fn
                
    @staticmethod
    def clear():
        Remote.functions = []
    
    @staticmethod
    def collated():
        collated = []
        c = Collator()
        classes, functions = c.collate(Remote.functions)
        for c in classes.keys():
            collated.append(c)
        for m in functions.keys():
            m.__name__ = m.__name__.split('.')[-1]
            collated.append(m)
        return collated


def __options(fn):
    """
    Ensure function has the gofer options attribute
    and return it.
    :param fn: A function
    :return: The function options object.
    :rtype: Options
    """
    if not hasattr(fn, NAME):
        opt = Options()
        opt.security = []
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
    secret = kwargs.get('secret', ())
    def df(fn):
        opt = __options(fn)
        if secret:
            required = Options()
            required.secret = secret
            auth = ('secret', required)
            opt.security.append(auth)
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
        required = Options()
        required.user = user
        required.service = service
        auth = ('pam', required)
        opt.security.append(auth)
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
    def df(fn):
        opt = __options(fn)
        required = Options()
        required.user = name
        auth = ('pam', required) 
        opt.security.append(auth)
        return fn
    if args:
        return df(args[0])
    else:
        return df
