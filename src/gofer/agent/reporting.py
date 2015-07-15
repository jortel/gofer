# Copyright (c) 2015 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Jeff Ortel <jortel@redhat.com>

import inspect

from gofer import NAME
from gofer.common import utf8


def indent(string, indent, *args):
    """
    Indent the specified string and replace arguments.
    :param string: A string.
    :param string: basestring
    :param indent: The number of spaces to indent.
    :type indent: int
    :param args: List of arguments.
    :type args: list
    :return: The indented string.
    :rtype: str
    """
    s = []
    for n in range(0, indent):
        s.append(' ')
    s.append(utf8(string) % args)
    return ''.join(s)


def signature(name, fn):
    """
    Build the signature for the specified function name and object.
    :param name: A function name.
    :type name: str
    :param fn: A function/method object.
    :type fn: function|method
    :return: The signature.
    :rtype: str
    """
    s = list()
    s.append(name)
    s.append('(')
    spec = inspect.getargspec(fn)
    if 'self' in spec[0]:
        spec[0].remove('self')
    if spec[1]:
        spec[0].append('*%s' % spec[1])
    if spec[2]:
        spec[0].append('**%s' % spec[2])
    s.append(', '.join(spec[0]))
    s.append(')')
    return ''.join(s)


def loaded(container, actions):
    """
    Report all loaded objects.
    :param container: The plugin container.
    :type container: gofer.agent.plugin.Container
    :param actions: The actions collection.
    :type actions: gofer.agent.decorator.Actions
    :return: The formatted report.
    :rtype: str
    """
    s = list()
    s.append('Plugins:')
    for p in container.all():
        if not p.enabled:
            continue
        # plugins
        s.append('')
        s.append(indent('<plugin> %s', 2, p.name))
        # classes
        s.append(indent('Classes:', 4))
        for name, thing in p.dispatcher.catalog.items():
            if inspect.ismodule(thing):
                continue
            s.append(indent('<class> %s', 6, name))
            s.append(indent('methods:', 8))
            for m_name, m_object in inspect.getmembers(thing, inspect.ismethod):
                fn = m_object.im_func
                if not hasattr(fn, NAME):
                    continue
                s.append(indent(signature(m_name, fn), 10))
        # functions
        s.append(indent('Functions:', 4))
        for name, thing in p.dispatcher.catalog.items():
            if not inspect.ismodule(thing):
                continue
            for f_name, f_object in inspect.getmembers(thing, inspect.isfunction):
                fn = f_object
                if not hasattr(fn, NAME):
                    continue
                s.append(indent(signature(f_name, fn), 6))
    s.append('')
    s.append('Actions:')
    for a in [(a.name(), a.interval) for a in actions.collated()]:
        s.append('  %s %s' % a)
    return '\n'.join(s)
