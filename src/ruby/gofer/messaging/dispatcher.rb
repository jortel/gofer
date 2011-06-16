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

require 'gofer/messaging/pkg'


class DispatchError < Exception ; end
        
class RemoteException < Exception ; end
  

class Return
  
  def initialize(hash)
    @hash = hash[:result]
  end

  def succeeded(h)
    return @hash.has_key?(:retval)
  end

  def failed()
    return ( !self.succeeded() )
  end
  
  def retval()
    return @hash[:retval]    
  end
  
  def exval()
    return @hash[:exval]    
  end
  
  def status()
    return @hash[:status]    
  end

end


class Dispatcher
end