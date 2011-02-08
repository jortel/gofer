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

from threading import RLock


# process name used to build the following paths:
#   /etc/<NAME>
#   /etc/<NAME>/agent.conf
#   /etc/<NAME>/conf.d
#   /etc/<NAME>/plugins
#   /var/lib/<NAME>
#   /var/lib/<NAME>/messaging
#   /usr/lib/<NAME>/<plugin>
#   /var/run/<NAME>d.pid
#   /var/log/<NAME>/agent.log
#   ~/.<NAME>/agent.conf
NAME = 'gofer'


class Singleton(type):
    """
    Singleton metaclass
    usage: __metaclass__ = Singleton
    """
    __mutex = RLock()

    def __init__(self, name, bases, ns):
        super(Singleton, self).__init__(name, bases, ns)
        self.instances = {}
        
    def __call__(self, *args, **kwargs):
        self.__mutex.acquire()
        try:
            key = (tuple(args), tuple(sorted(kwargs.items())))
            inst = self.instances.get(key)
            if inst is None: 
                inst = super(Singleton, self).__call__(*args, **kwargs)
                self.instances[key] = inst
            return inst
        finally:
            self.__mutex.release()