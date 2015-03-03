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

from gofer.collator import Collator


class Remote:

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
