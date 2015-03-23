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

from gofer.decorators import remote
from gofer.rmi.shell import Shell


class Package(object):
    """
    RPM package management using YUM.
    """

    @remote
    def install(self, name):
        """
        Install a package by name.
        :param name: A complete or partial package name.
        :type name: str
        :return: (status, {stdout:<str>, stderr:<str>})
        :rtype: tuple
        """
        shell = Shell()
        return shell.run('yum', 'install', name, '-y')

    @remote
    def update(self, name=''):
        """
        Update a package by (optional) name.
        :param name: A complete or partial package name.
        :type name: str
        :return: (status, {stdout:<str>, stderr:<str>})
        :rtype: tuple
        """
        shell = Shell()
        return shell.run('yum', 'update', name, '-y')

    @remote
    def remove(self, name):
        """
        Remove a package by name.
        :param name: A complete or partial package name.
        :type name: str
        :return: (status, {stdout:<str>, stderr:<str>})
        :rtype: tuple
        """
        shell = Shell()
        return shell.run('yum', 'remove', name, '-y')
