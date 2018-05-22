#
# Copyright (c) 2018 Red Hat, Inc.
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
Provided to support PY3/PY3 compatibility.
"""

import inspect

from six import PY2, get_unbound_function

from gofer.compat import str


def mro(cls):
    """
    Get method resolution order.

    Args:
        cls (class): A class to inspect.

    Returns:
        tuple: Tuple of class.
    """
    return inspect.getmro(cls)


def classes(mod, name=None):
    """
    Get a list of all classes know to a function.

    Args:
        mod (module): A module to inspect.
        name (str): A class name.

    Returns:
        list: of class.
    """
    members = []
    for member in inspect.getmembers(mod, predicate=inspect.isclass):
        if not name or member[0] == name:
            members.append(member)
    return members


def module(fn):
    """
    Get the module for a function.

    Args:
        fn (function): A function to inspect.

    Returns:
        module: A module.
    """
    return inspect.getmodule(fn)


def method(cls, name):
    """
    Get a specific method by name.

    Args:
        cls(class): A class to inspect.
        name (str): A method name.

    Returns:
        function: The method function.
    """
    assert inspect.isclass(cls), 'Must be class.'

    return methods(cls, name=name)[0][1]


def methods(cls, name=None):
    """
    Get all of the class methods.

    Args:
        cls(class): A class to inspect.
        name (str): A method name.

    Returns:
        list: of (name, function)
    """
    assert inspect.isclass(cls), 'Must be class.'

    def predicate(m):
        return inspect.ismethod(m) or inspect.isfunction(m)

    members = []
    for m in inspect.getmembers(cls, predicate=predicate):
        if inspect.ismethod(m[1]):
            m = (m[0], get_unbound_function(m[1]))
        members.append(m)
    return [
        m for m in members if not name or m[0] == name
    ]


def functions(mod, name=None):
    """
    Get all of the functions contained in a module.

    Args:
        mod(class): A module to inspect.
        name (str): A method name.

    Returns:
        list: of (name, function)
    """
    members = []
    for member in inspect.getmembers(mod, predicate=inspect.isfunction):
        if not name or member[0] == name:
            members.append(member)
    return members


def signature(fn):
    """
    Get a function signature.

    Args:
        fn (function): A function to inspect.

    Returns:
        str: String representation of the signature.
    """
    assert inspect.isfunction(fn), 'Must be function.'

    if PY2:
        sp = inspect.getargspec(fn)
        return inspect.formatargspec(
            args=sp.args,
            varkw=sp.keywords,
            varargs=sp.varargs,
            defaults=sp.defaults)
    else:
        return str(inspect.signature(fn))


def is_module(thing):
    """
    Get whether an object is a module.

    Args:
        thing (object): An object.

    Returns:
        bool: True if a module.

    """
    return inspect.ismodule(thing)


def is_class(thing):
    """
    Get whether an object is a class.

    Args:
        thing (object): An object.

    Returns:
        bool: True if a class.

    """
    return inspect.isclass(thing)


def is_function(thing):
    """
    Get whether an object is a function.

    Args:
        thing (object): An object.

    Returns:
        bool: True if a function.

    """
    return inspect.isfunction(thing)
