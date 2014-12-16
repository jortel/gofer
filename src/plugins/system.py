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

from subprocess import Popen, PIPE, call
from gofer.decorators import *
from gofer.agent.plugin import Plugin
from gofer.pam import authenticate
from logging import getLogger

log = getLogger(__name__)
plugin = Plugin.find(__name__)


class System:
    
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
        :see: shutdown(8)
        """
        command = 'shutdown -h %s &' % when
        call(command, shell=True)

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
        :see: shutdown(8)
        """
        command = 'shutdown -r %s &' % when
        call(command, shell=True)
        
    @remote
    @pam(user='root')
    def cancel(self):
        """
        Cancel a scheduled shutdown; halt() or reboot().
        """
        call('shutdown -c', shell=True)


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
        authenticate(user, password)
        command = ('su', '-', user, '-c', cmd)
        p = Popen(command, stdout=PIPE)
        try:
            result = p.stdout.read()
            p.stdout.close()
            status = p.wait()
            return status, result
        except OSError, e:
            return -1, str(e)
