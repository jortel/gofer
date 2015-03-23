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

STDOUT = 'stdout'
STDERR = 'stderr'


class Shell(object):
    """
    Shell used to execute commands.
    """

    def run(self, *command):
        """
        Run the specified command.
        :param command: A command and parameters.
        :type command: tuple
        :return: (status, {stdout:<str>, stderr:<str>})
        :rtype: tuple
        """
        details = {
            STDOUT: '',
            STDERR: '',
        }
        result = {
            STDOUT: '',
            STDERR: '',
        }
        context = Context.current()
        context.progress.details = details
        p = Popen(command, stdout=PIPE, stderr=PIPE)
        try:
            while True:
                n_read = 0
                if context.cancelled():
                    p.terminate()
                    break
                for fp, key in ((p.stdout, STDOUT), (p.stderr, STDERR)):
                    line = fp.readline()
                    if line:
                        n_read += len(line)
                        details[key] = line
                        result[key] += line
                        context.progress.report()
                if not n_read:
                    #  EOF
                    break
            p.stdout.close()
            p.stderr.close()
            status = p.wait()
            return status, result
        except OSError, e:
            return -1, utf8(e)
