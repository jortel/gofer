# Copyright (c) 2015 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Jeff Ortel (jortel@redhat.com)

from qpid.messaging import NotFound as _NotFound

from gofer.messaging.adapter.model import NotFound


def reliable(fn):
    def _fn(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except _NotFound, e:
            raise NotFound(*e.args)
    return _fn