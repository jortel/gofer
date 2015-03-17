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

from threading import RLock
from gofer import Singleton, synchronized, utf8


class Whiteboard:
    """
    Provides a dict-like object used to publish
    information to other plugins.
    """
    
    __metaclass__ = Singleton
    
    def __init__(self):
        self.__dict = {}
        self.__mutex = RLock()
        
    @synchronized
    def get(self, name, default=None):
        return self.__dict.get(name, default)
    
    @synchronized
    def update(self, d):
        self.__dict.update(d)
    
    @synchronized
    def __getitem__(self, name):
        return self.__dict[name]
    
    @synchronized
    def __setitem__(self, name, value):
        self.__dict[name] = value

    @synchronized
    def __repr__(self):
        return repr(self.__dict)
    
    @synchronized
    def __unicode__(self):
        return unicode(self.__dict)

    @synchronized
    def __str__(self):
        return utf8(self)
