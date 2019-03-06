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

from gofer.collation import Class, Module


def indent(string, n, *args, **kwargs):
    """
    Indent the specified string and replace arguments.
    :param string: A string.
    :param string: str
    :param n: The number of spaces to indent.
    :type n: int
    :param args: List of arguments.
    :type args: list
    :return: The indented string.
    :rtype: str
    """
    s = []
    for n in range(0, n):
        s.append(' ')
    s.append(str(string).format(*args, **kwargs))
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
        s.append('')
        s.append(indent('<plugin> {}', 2, p.name))
        s.append(indent('Classes:', 4))
        for name, thing in sorted(p.dispatcher.catalog.items()):
            if isinstance(thing, Module):
                continue
            s.append(indent('<class> {}', 6, name))
            s.append(indent('Methods:', 8))
            for method in sorted(thing):
                s.append(indent(str(method), 10))
        s.append(indent('Functions:', 4))
        for name, thing in sorted(p.dispatcher.catalog.items()):
            if isinstance(thing, Class):
                continue
            for fn in sorted(thing):
                s.append(indent(str(fn), 6))
    s.append('')
    s.append('Actions:')
    for a in sorted([(a.name, a.interval) for a in actions.collated()]):
        s.append(indent('{} {}', 2, *a))
    return '\n'.join(s)
