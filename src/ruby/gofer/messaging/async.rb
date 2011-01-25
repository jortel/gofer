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

require 'gofer/messaging/consumer'
require 'gofer/messaging/dispatcher'

class AsyncConsumer < Consumer
  
  def start(listener)
    @listener = listener
    super.start()
  end
  
  def dispatch(envelope)
    begin
      reply = getreply(envelope)
      reply.notify(@listener)
    rescue Exception=>e
      puts "Exception: #{e.to_s}"
    end
  end
  
  private
  
  def getreply(envelope)
    if envelope[:status]
      return Status.new(envelope)
    end
    result = Return.new(envelope[:result])
    if result.succeeded():
      return Succeeded(envelope)
    else
      return Failed(envelope)
    end    
  end
  
end


class AsyncReply
  
  def initialize(envelope)
    @sn = envelope[:sn]
    @origin = envelope[:origin]
    @any = envelope[:any]    
  end
  
  def notify(listener)
    abstract_method
  end
  
  def to_s()
    s = [self.class.name]
    s << "sn: #{@sn}"
    s << "origin: #{@origin}"
    s << "user data: #{@any}"
    return s.join('\n')
  end
end


class FinalReply < AsyncReply

  def notify(listener)
    if self.succeeded()
      listener.succeeded(self)
    else
      listener.failed(self)
    end
  end
  
  def succeeded()
    return false
  end
  
  def failed()
    return (! self.succeeded())
  end
  
  def throw() ; end
end


class Succeeded < FinalReply
  
  def initialize(envelope)
    super(envelope)
    reply = Return.new(envelope[:result])
    @retval = reply.retval()
  end

  def succeeded()
    return true
  end

  def to_s()
    s = [super.to_s()]
    s << "  retval: "
    s << @retval.to_s
    return s.join('\n')
  end
end


class Failed < FinalReply

  def initialize(envelope)
    super(envelope)
    reply = Return.new(envelope[:result])
    @exval = RemoteException.new(reply.exval)
  end
  
  def throw()
    raise @exval
  end
end


class Status < AsyncReply

  def initialize(envelope)
    super(envelope)
    @status = envelope[:status]    
  end
  
  def notify(listener)
    listener.status(self)
  end
  
  def to_s()
    s = [super.to_s()]
    s << "  status: "
    s << @status
    return s.join('\n')
  end
end


class Listener

  def succeeded(reply) ; end    
  def failed(reply) ; end
  def status(reply) ; end
    
end