# Copyright (c) 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import os
import sys

sys.path.insert(0, os.path.join(os.path.curdir, '../../src'))

from logging import basicConfig

from base import Test
from gofer.transport import Transport


basicConfig()

URL = 'tcp://localhost:5672'

if __name__ == '__main__':
    Transport.load_plugins()
    # AMQP-0-10
    package = Transport.plugins['AMQP-0-10']
    test = Test(URL, package)
    test()
    # qpid
    package = Transport.plugins['qpid']
    test = Test(URL, package)
    test()
    # qpid-messaging
    package = Transport.plugins['qpid-messaging']
    test = Test(URL, package)
    test()