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

import libvirt
from gofer.decorators import *
from gofer.agent.plugin import Plugin
from logging import getLogger

log = getLogger(__name__)
plugin = Plugin.find(__name__)


class Virt:
    
    @classmethod
    def open(cls):
        cfg = plugin.cfg()
        con = libvirt.open(cfg.virt.uri)
        return con
        
    @remote
    def getDomainID(self, name):
        """
        Resolve a domain name to a domain ID.
        :param name: A domain name.
        :type name: str
        :return: A domain ID.
        :rtype: int
        """
        con = self.open()
        try:
            domain = con.lookupByName(name)
            return domain.ID()
        finally:
            con.close()
    
    @remote
    def listDomains(self):
        """
        Get a list of domains.
        :return: List of dict: {id, name, active}
        :rtype: list
        """
        con = self.open()
        try:
            domains = []
            for id in con.listDomainsID():
                domain = con.lookupByID(id)
                d = dict(id=id,
                         name=domain.name(),
                         active=domain.isActive())
                domains.append(d)
            return domains
        finally:
            con.close()
            
    @remote
    def isAlive(self, id):
        """
        Get whether a domain is alive (running).
        :param id: A domain ID.
        :type id: int
        :return: True if alive.
        :rtype: bool
        """
        con = self.open()
        try:
            domain = con.lookupByID(id)
            return domain.isAlive()
        finally:
            con.close()
            
    @remote
    @pam(user='root')
    def start(self, id):
        """
        Start (create) a domain.
        :param id: A domain ID.
        :type id: int
        """
        con = self.open()
        try:
            domain = con.lookupByID(id)
            domain.create()
        finally:
            con.close()
        
    @remote
    @pam(user='root')
    def shutdown(self, id):
        """
        Shutdown a domain.
        :param id: A domain ID.
        :type id: int
        """
        con = self.open()
        try:
            domain = con.lookupByID(id)
            domain.shutdown()
        finally:
            con.close()