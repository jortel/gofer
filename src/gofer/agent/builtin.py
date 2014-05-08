# Copyright (c) 2014 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
# Jeff Ortel <jortel@redhat.com>

"""
Builtin plugin.
"""

import inspect

from logging import getLogger

from gofer.decorators import remote
from gofer.rmi.tracker import Tracker
from gofer.rmi.criteria import Builder
from gofer.agent.plugin import Plugin
from gofer.agent.action import Actions


log = getLogger(__name__)


def indent(v, n, *args):
    s = []
    for n in range(0, n):
        s.append(' ')
    s.append(str(v) % args)
    return ''.join(s)


def signature(n, fn):
    s = list()
    s.append(n)
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


class Admin:

    @remote
    def cancel(self, sn=None, criteria=None):
        """
        Cancel by serial number or user defined property.
        :param sn: An RMI serial number.
        :type sn: str
        :param criteria: The criteria used to match the
            *any* property on an RMI request.
        :type criteria: str
        :return: The list of cancelled serial numbers.
        :rtype: list
        :raise Exception, on (sn) not found.
        :see: gofer.rmi.criteria
        """
        sn_list = []
        cancelled = []
        tracker = Tracker()
        if sn:
            sn_list = [sn]
        if criteria:
            b = Builder()
            criteria = b.build(criteria)
            sn_list = tracker.find(criteria)
        for sn in sn_list:
            _sn = tracker.cancel(sn)
            if _sn:
                cancelled.append(_sn)
        return cancelled

    @remote
    def hello(self):
        return 'Hello, I am gofer agent'

    @remote
    def help(self):
        s = list()
        s.append('Plugins:')
        for p in Plugin.all():
            if not p.enabled():
                continue
            # plugin
            s.append('')
            s.append(indent('<plugin> %s', 2, p.name))
            # classes
            s.append(indent('Classes:', 4))
            for n, v in p.dispatcher.catalog.items():
                if inspect.ismodule(v):
                    continue
                s.append(indent('<class> %s', 6, n))
                s.append(indent('methods:', 8))
                for n, v in inspect.getmembers(v, inspect.ismethod):
                    fn = v.im_func
                    if not hasattr(fn, 'gofer'):
                        continue
                    s.append(indent(signature(n, fn), 10))
            # functions
            s.append(indent('Functions:', 4))
            for n, v in p.dispatcher.catalog.items():
                if not inspect.ismodule(v):
                    continue
                for n, v in inspect.getmembers(v, inspect.isfunction):
                    fn = v
                    if not hasattr(fn, 'gofer'):
                        continue
                    s.append(indent(signature(n, fn), 6))
        s.append('')
        s.append('Actions:')
        for a in [(a.name(), a.interval) for a in Actions().collated()]:
            s.append('  %s %s' % a)
        return '\n'.join(s)
