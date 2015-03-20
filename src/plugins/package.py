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

from subprocess import Popen, PIPE

from gofer import utf8
from gofer.agent.rmi import Context
from gofer.decorators import remote


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
        :return: tuple (status, output)
        :rtype: tuple
        """
        command = ('yum', 'install', name, '-y')
        return self.run(command)

    @remote
    def update(self, name=''):
        """
        Update a package by (optional) name.
        Update ALL when name is not specified.
        :param name: A complete or partial package name.
        :type name: str
        :return: tuple (status, output)
        :rtype: tuple
        """
        command = ('yum', 'update', name, '-y')
        return self.run(command)

    @remote
    def remove(self, name):
        """
        Remove a package by name.
        :param name: A complete or partial package name.
        :type name: str
        :return: tuple (status, output)
        :rtype: tuple
        """
        command = ('yum', 'remove', name, '-y')
        return self.run(command)

    def run(self, command):
        context = Context.current()
        context.progress.details = ''
        p = Popen(command, stdout=PIPE, stderr=PIPE)
        try:
            while True:
                if context.cancelled():
                    p.terminate()
                    break
                output = p.stdout.read(120)
                if output:
                    context.progress.details += output
                    context.progress.report()
                else:
                    break
            result = context.progress.details
            p.stdout.close()
            p.stderr.close()
            status = p.wait()
            return status, result
        except OSError, e:
            return -1, utf8(e)
