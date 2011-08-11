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

require 'gofer/rmi/container'
require 'gofer/messaging/producer'

module Gofer
  
  class Agent < Container
  
    # options:
    #  url      - (str|URL) A broker URL.
    #  ctag     - (str) Async correlateion tag.
    #  async    - (bool) Async invocation flag.
    #  window   - (Window) Maintenance window.
    #  any      - (object) Any data to be round-tripped on each request.
    #  producer - (Producer) A configured amqp producer
    #  timeout  - (int|Array[2]) Synchronous timeout value.
    #
    def initialize(uuid, options={})
      super(uuid, options)
    end

  end

end