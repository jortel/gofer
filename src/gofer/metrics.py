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
The I{metrics} module defines classes and other resources
designed for collecting and reporting performance metrics.
"""

import time
from math import modf

class Timer:

    def __init__(self, started=0, stopped=0):
        self.started = started
        self.stopped = stopped

    def start(self):
        self.started = time.time()
        self.stopped = 0
        return self

    def stop(self):
        if self.started > 0:
            self.stopped = time.time()
        return self

    def duration(self):
        return ( self.stopped - self.started )

    def __str__(self):
        if self.started == 0:
            return 'not-running'
        if self.started > 0 and self.stopped == 0:
            return 'started: %d (running)' % self.started
        duration = self.duration()
        jmod = ( lambda m : (m[1], m[0]*1000) )
        if duration < 1:
            ms = (duration*1000)
            return '%d (ms)' % ms           
        if duration < 60:
            m = modf(duration)
            return '%d.%.3d (seconds)' % jmod(m)
        m = modf(duration/60)
        return '%d.%.3d (minutes)' % jmod(m)
