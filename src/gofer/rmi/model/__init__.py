#
# Copyright (c) 2016 Red Hat, Inc.
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
RMI call models.
"""

from gofer.rmi.model import direct, fork

# call models
DIRECT = 'direct'
FORK = 'fork'

ALL = {
    DIRECT: direct.Call,
    FORK: fork.Call,
}


def valid_model(model):
    if model in ALL:
        return model
    else:
        raise ValueError('model must be: %s' % '|'.join(ALL))
