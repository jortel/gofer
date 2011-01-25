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

require 'gofer/messaging/pkg'


class DispatchError < Exception ; end
        
class RemoteException < Exception ; end
  

class Return
  
  def initialize(hash)
    @hash = hash['result']
  end

  def succeeded(h)
    return @hash.has_key?('retval')
  end

  def failed()
    return ( !self.succeeded() )
  end
  
  def retval()
    return @hash['retval']    
  end
  
  def exval()
    return @hash['exval']    
  end
  
  def status()
    return @hash['status']    
  end

end


class Dispatcher
end