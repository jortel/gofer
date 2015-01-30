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

from logging import basicConfig

from base import Test
from gofer.messaging.adapter.factory import Loader


basicConfig()

URL = 'amqp://localhost:5673'

if __name__ == '__main__':
    loader = Loader()
    loader.load()
    # AMQP-0-9-1
    adapter = loader.catalog['amqp-0-9-1']
    test = Test(URL, adapter)
    test()
    # amqp
    adapter = loader.catalog['amqp']
    test = Test(URL, adapter)
    test()
