#! /usr/bin/env python
#
# Copyright (c) 2010 Red Hat, Inc.
#
# Authors: Jeff Ortel <jortel@redhat.com>
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
#

from gofer.messaging import mock

mock.install()

from server import main

class BadDog:
    
    def bark(self, words):
        return 'I will not bark for you!'
    
    def wag(self, n):
        return 'I will not wag for you!'
    
    def sleep(self, n):
        pass
    
mock.register(Dog=BadDog)

if __name__ == '__main__':
    uuid = 'xyz'
    main(uuid)
    h = mock.history()
    print 'Call History:'
    for stub, calls in h.calls(uuid).items():
        print '%s:' % stub
        for call in calls:
            print '  %s' % str(call)
    print 'finished.'


