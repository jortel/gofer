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

require 'gofer/messaging/consumer'
require 'gofer/messaging/dispatcher'

class ReplyConsumer < Consumer
  
  def start(listener)
    @listener = listener
    super.start()
  end
  
  def dispatch(envelope)
    begin
      reply = getreply(envelope)
      reply.notify(@listener)
    rescue Exception=>e
      @log.info("Exception: #{e.to_s}")
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