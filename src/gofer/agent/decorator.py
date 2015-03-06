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
Action class for gofer agent.
"""

from logging import getLogger

from gofer.collator import Collator
from gofer.agent.action import Action


log = getLogger(__name__)


class Actions:
    """
    :cvar functions: The list of decorated functions.
    """
    functions = {}
    
    @staticmethod
    def add(fn, interval):
        Actions.functions[fn] = interval

    @staticmethod
    def clear():
        """
        Clear the list of actions.
        """
        Actions.functions = {}
    
    @staticmethod
    def collated():
        collated = []
        collator = Collator()
        classes, functions = collator.collate(Actions.functions)
        for _class, methods in classes.items():
            inst = _class()
            for method, options in methods:
                method = getattr(inst, method.__name__)
                action = Action(method, **options)
                collated.append(action)
        for module, fn_list in functions.items():
            for function, options in fn_list:
                action = Action(function, **options)
                collated.append(action)
        return collated


class Delegate(object):
    """
    Plugin delegate functions.
    :cvar load: Decorated plugin load function.
    :type load: list
    :cvar unload: Decorated plugin unload function.
    :type unload: list
    """

    load = []
    unload = []

    def __init__(self):
        self.load = Delegate.load
        self.unload = Delegate.unload
        Delegate.load = []
        Delegate.unload = []

    def loaded(self):
        """
        Plugin loaded.
        """
        for fn in self.load:
            fn()

    def unloaded(self):
        """
        Plugin unloaded.
        """
        for fn in self.unload:
            try:
                fn()
            except Exception:
                log.exception(str(fn))