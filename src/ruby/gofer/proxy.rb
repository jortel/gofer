#
# Copyright (c) 2010 Red Hat, Inc.
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

require 'gofer/messaging/base'
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