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

class Singleton(type):
    """
    Singleton metaclass
    usage: __metaclass__ = Singleton
    """

    def __init__(self, name, bases, ns):
        super(Singleton, self).__init__(name, bases, ns)
        self.instances = {}
        
    def __call__(self, *args, **kwargs):
        key = (tuple(args), tuple(sorted(kwargs.items())))
        inst = self.instances.get(key)
        if inst is None: 
            inst = super(Singleton, self).__call__(*args, **kwargs)
            self.instances[key] = inst
        return inst