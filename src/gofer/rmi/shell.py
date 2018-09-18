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

from gofer.rmi.context import Context


STDOUT = 'stdout'
STDERR = 'stderr'


class Shell(object):
    """
    Shell used to execute commands.
    :ivar progress_reported: Enables progress reporting.
    :type progress_reported: bool
    """

    def __init__(self):
        self.progress_reported = True

    def report(self, details):
        """
        Report progress.
        :param details: The details to report.
        :type details: dict
        """
        if not self.progress_reported:
            # not enabled
            return
        context = Context.current()
        context.progress.details = details
        context.progress.report()

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
                        self.report(details)
                if not n_read:
                    #  EOF
                    break
            p.stdout.close()
            p.stderr.close()
            status = p.wait()
            return status, result
        except OSError as e:
            return -1, str(e)
