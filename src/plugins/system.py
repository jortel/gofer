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
System plugin.
"""

import os

from gofer.decorators import pam, remote
from gofer.rmi.shell import Shell as _Shell
from gofer.pam import authenticate


class System(object):
    
    @remote
    @pam(user='root')
    def halt(self, when=1):
        """
        Halt the system.
        :param when: When to perform the shutdown.
          One of:
            - now   : immediate.  note: reply not sent.
            - +m    : where m is minutes.
            - hh:mm : time (hours:minutes) 24hr clock.
        :type when: str
        :return: (status, {stdout:<str>, stderr:<str>})
        :rtype: tuple
        :see: shutdown(8)
        """
        shell = _Shell()
        return shell.run('shutdown', '-h', when, '&')

    @remote
    @pam(user='root')
    def reboot(self, when=1):
        """
        Reboot the system.
        :param when: When to perform the reboot.
          One of:
            - now   : immediate.  note: reply not sent.
            - +m    : where m is minutes.
            - hh:mm : time (hours:minutes) 24hr clock.
        :type when: str
        :return: (status, {stdout:<str>, stderr:<str>})
        :rtype: tuple
        :see: shutdown(8)
        """
        shell = _Shell()
        return shell.run('shutdown', '-r', when, '&')
        
    @remote
    @pam(user='root')
    def cancel(self):
        """
        Cancel a scheduled shutdown; halt() or reboot().
        :return: (status, {stdout:<str>, stderr:<str>})
        :rtype: tuple
        :see: shutdown(8)
        """
        shell = _Shell()
        return shell.run('shutdown', '-c')


class Service(object):
    """
    Services management.
    """

    def __init__(self, name):
        """
        :param name: The service name.
        :rtype name: str
        """
        self.name = name

    @remote
    @pam(user='root')
    def start(self):
        """
        Start the named service.
        :return: (status, {stdout:<str>, stderr:<str>})
        :rtype: tuple
        """
        shell = _Shell()
        return shell.run('service', self.name, 'start')

    @remote
    @pam(user='root')
    def stop(self):
        """
        Stop the named service.
        :return: (status, {stdout:<str>, stderr:<str>})
        :rtype: tuple
        """
        shell = _Shell()
        return shell.run('service', self.name, 'stop')

    @remote
    @pam(user='root')
    def restart(self):
        """
        Restart the named service.
        :return: (status, {stdout:<str>, stderr:<str>})
        :rtype: tuple
        """
        shell = _Shell()
        return shell.run('service', self.name, 'restart')

    @remote
    def status(self):
        """
        Get the *status* of the named service.
        :return: (status, {stdout:<str>, stderr:<str>})
        :rtype: tuple
        """
        shell = _Shell()
        return shell.run('service', self.name, 'status')


class Shell:

    @remote
    def run(self, cmd, user, password):
        """
        Run a shell command.
        The command is executed as: "su - <user> -c <cmd>" and the
        user/password is authenticated using PAM.
        :param cmd: The command & arguments.
        :type cmd: str
        :param user: A user name.
        :type user: str
        :param password: The password.
        :type password: str
        :return: tuple (status, output)
        :rtype: tuple
        """
        if authenticate(user, password):
            shell = _Shell()
            return shell.run('su', '-', user, '-c', cmd)
        else:
            return os.EX_NOPERM, {}
