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

from gofer import NAME, Options
from gofer.rmi.decorator import Remote
from gofer.agent.decorator import Actions
from gofer.agent.decorator import Delegate


def options(fn):
    """
    Add base options.
    :param fn: A function.
    :type fn: function
    :return: The base options.
    :rtype: Options
    """
    if not hasattr(fn, NAME):
        opt = Options()
        opt.security = []
        setattr(fn, NAME, opt)
    else:
        opt = getattr(fn, NAME)
    return opt


def remote(fx=None, secret=None):
    """
    The *remote* decorator.
    Used to expose function/methods as RMI targets.
    :param secret: An optional shared secret.
    :type secret: str
    :return: The decorated function.
    """
    def inner(fn):
        opt = options(fn)
        if secret:
            required = Options()
            required.secret = secret
            auth = ('secret', required)
            opt.security.append(auth)
        Remote.add(fn)
        return fn
    if inspect.isfunction(fx):
        return inner(fx)
    else:
        return inner


def pam(user, service=None):
    """
    The *pam* decorator.
    This security decorator is used to specify that the
    function requires PAM authentication.  The *user* and *password* passed
    in the RMI request is authenticated using PAM.  The *user* in the RMI
    request _must_ match the *user* specified here.
    :param user: The user name.
    :type user: str
    :param service: The optional PAM server used for authentication.
    :type service: str
    :return: The decorated function.
    """
    def inner(fn):
        opt = options(fn)
        required = Options()
        required.user = user
        required.service = service
        auth = ('pam', required)
        opt.security.append(auth)
        return fn
    return inner


def user(name=None):
    """
    The *user* decorator.
    This security decorator is used to specify that the
    function requires PAM authentication.  The *user* and *password* passed
    in the RMI request is authenticated using PAM.  The *user* in the RMI
    request _must_ match the *name* specified here.
    :param name: The user name.
    :type name: str
    :return: The decorated function.
    """
    def inner(fn):
        opt = options(fn)
        required = Options()
        required.user = name
        required.service = None
        auth = ('pam', required)
        opt.security.append(auth)
        return fn
    return inner


def action(**interval):
    """
    The *action* decorator.
    Used to designate a function/method as being a recurring action.
    :keyword interval: The run interval.
      One of:
        - days
        - seconds
        - minutes
        - hours
        - weeks
    :type interval: dict
    :return: The decorated function.
    """
    def inner(fn):
        Actions.add(fn, interval)
        return fn
    return inner


def load(fn):
    """
    The *load* decorator.
    Used to designate a function/method to be called
    after a plugin is loaded.  This is and opportunity to
    perform any additional plugin setup.  Called after a plugin
    has been successfully loaded.
    :param fn: A function/method.
    :type fn: function
    :return: The decorated function.
    """
    Delegate.load.append(fn)
    return fn


def unload(fn):
    """
    The *unload* decorator.
    Used to designate a function/method to be called
    after a plugin is unloaded.  This is and opportunity to
    clean up resources.  Called after a plugin has been unloaded.
    :param fn: A function/method.
    :type fn: function
    :return: The decorated function.
    """
    Delegate.unload.append(fn)
    return fn


# backwards compatibility
initializer = load