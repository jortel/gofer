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

from gofer import inspection
from gofer.collation import Collator


class Remote:
    """
    Collection of @remote decorated functions (method-functions).
    """

    functions = []

    @staticmethod
    def add(fn):
        """
        Add the specified function.

        Args:
            fn (function): A function to be added.
        """
        Remote.functions.append(fn)

    @staticmethod
    def purge(mod):
        """
        Purge functions for the specified module.

        Args:
            mod (module): A module.
        """
        purged = []
        for fn in Remote.find(mod):
            purged.append(fn)
        for fn in purged:
            Remote.functions.remove(fn)

    @staticmethod
    def find(mod):
        """
        Yield all functions in the specified module.

        Args:
            mod (module): A module.

        Yields:
            function: Each function.
        """
        for fn in Remote.functions:
            if inspection.module(fn) == mod:
                yield fn

    @staticmethod
    def clear():
        """
        Clear the collection of functions.
        """
        Remote.functions = []

    @staticmethod
    def collated():
        """
        Get a collated list of @remote decorated functions.

        Returns:
            list: Of (gofer.collation.Class|gofer.collation.Module)
        """
        collated = []
        collator = Collator()
        classes, functions = collator({f: {} for f in Remote.functions})
        collated.extend(classes)
        collated.extend(functions)
        return collated
