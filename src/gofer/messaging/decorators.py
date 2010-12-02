#
# Copyright (c) 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
#

"""
Provides decorator classes & funcitons.
"""

from gofer.collator import Collator


class Remote:
    """
    @cvar functions: The list of decorated functions.
    """
    functions = []
    
    def collated(self):
        collated = []
        c = Collator()
        classes, functions = c.collate(self.functions)
        for c in classes.keys():
            collated.append(c)
        for m in functions.keys():
            collated.append(m)
        return collated
            

def remote(fn):
    """
    Decorator used to register remotable classes.
    @param fn: A method/function to register.
    @type fn: function.
    """
    fn.remotepermitted = 1
    Remote.functions.append(fn)
    return fn
