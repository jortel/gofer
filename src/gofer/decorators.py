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

from gofer import NAME, Options
from gofer import inspection
from gofer.rmi.decorator import Remote
from gofer.rmi.model import DIRECT, FORK, valid_model
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
        opt.call = Options(model=DIRECT)
        setattr(fn, NAME, opt)
    else:
        opt = getattr(fn, NAME)
    return opt


def remote(fx=None, model=DIRECT):
    """
    The *remote* decorator.
    Used to expose function/methods as RMI targets.
    :param fx: The function being decorated when called without params.
    :type fx: function
    :param model: The RMI call model (direct|forked)
    :type model: str
    :return: The decorated function.
    """
    def inner(fn):
        opt = options(fn)
        opt.call.model = valid_model(model)
        Remote.add(fn)
        return fn
    if inspection.is_function(fx):
        return inner(fx)
    else:
        return inner


def direct(fn):
    """
    The *direct* decorator used to specify the *direct* model.
    :param fn: The function being decorated.
    :type fn: function
    :return: The decorated function.
    """
    opt = options(fn)
    opt.call.model = valid_model(DIRECT)
    return fn


def fork(fn):
    """
    The *fork* decorator used to specify the *fork* model.
    :param fn: The function being decorated.
    :type fn: function
    :return: The decorated function.
    """
    opt = options(fn)
    opt.call.model = valid_model(FORK)
    return fn


def action(fx=None, **interval):
    """
    The *action* decorator.
    Used to designate a function/method as being a recurring action.
    No interval can be used to specify the action to run only once.
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
        Actions.add(fn, interval or dict(days=0x8E94))
        return fn
    if inspection.is_function(fx):
        return inner(fx)
    else:
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
