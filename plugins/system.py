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

from gofer.decorators import remote
from gofer.rmi.shell import Shell as _Shell
from gofer.agent.rmi import Context


class System(object):
    
    @remote
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
    def start(self):
        """
        Start the named service.
        :return: (status, {stdout:<str>, stderr:<str>})
        :rtype: tuple
        """
        shell = _Shell()
        return shell.run('service', self.name, 'start')

    @remote
    def stop(self):
        """
        Stop the named service.
        :return: (status, {stdout:<str>, stderr:<str>})
        :rtype: tuple
        """
        shell = _Shell()
        return shell.run('service', self.name, 'stop')

    @remote
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

    def __init__(self, user, password):
        """
        :param user: A user name.
        :type user: str
        :param password: The password.
        :type password: str
        """
        self.user = user
        self.password = password

    @remote
    def run(self, cmd):
        """
        Run a shell command.
        The command is executed as: "su - <user> -c <cmd>".
        :param cmd: The command & arguments.
        :type cmd: str

        :return: (status, {stdout:<str>, stderr:<str>})
        :rtype: tuple
        """
        shell = _Shell()
        return shell.run('su', '-', self.user, '-c', cmd)


class Script:

    def __init__(self, content):
        """
        :param content: The script content.
        :type content: str
        """
        self.content = content

    @remote
    def run(self, user, password, *options):
        """
        Run a shell command.
        The command is executed as: "su - <user> -c <cmd>".
        :param user: A user name.
        :type user: str
        :param password: The password.
        :type password: str
        :param options: List of options.
        :type options: list
        :return: (status, {stdout:<str>, stderr:<str>})
        :rtype: tuple
        """
        shell = _Shell()
        context = Context.current()
        path = os.path.join('/tmp', context.sn)
        with open(path, 'w+') as fp:
            fp.write(self.content)
        try:
            os.chmod(path, 0o755)
            cmd = [path]
            cmd += options
            cmd = ' '.join(cmd)
            return shell.run('su', '-', user, '-c', cmd)
        finally:
            os.unlink(path)
