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
require 'gofer/messaging/consumer'
require 'gofer/messaging/dispatcher'

class RequestTimeout < Exception ; end


class RequestMethod

  def initialize(producer)
    @producer = producer    
  end
  
  def send(address, request, any={})
    abstract_method
  end
  
  def broadcast(addresses, request, any={}) ; end
  
  def close()
    @producer.close()
  end

end


class Synchronous < RequestMethod
  
  def initialize(producer, timeout)
    super(producer)
    @timeout = (timeout.is_a?(Array) ? timeout : [timeout])
    @queue = Gofer::Queue.new(getuuid(), false)
    @reader = Reader.new(@queue, nil, producer.url)
    @reader.start()
  end
  
  def send(destination, request, any={})
    body = {
      :replyto=>@queue.to_s,
      :request=>request
    }
    body.update(any)
    ttl = @timeout[0]
    sn = @producer.send(destination, body, ttl)
    getstarted(sn)
    return getreply(sn)
  end

  protected

  def getstarted(sn)
    envelope = @reader.search(sn, @timeout[0])
    if !envelope.nil?:
      @reader.ack()
      if envelope['status']
        puts "request (#{sn}), started"
      else
        onreply(envelope)
      end
    else
      raise RequestTimeout.new(sn)
    end
  end

  def getreply(sn)
    envelope = @reader.search(sn, @timeout[1])
    if !envelope.nil?:
      @reader.ack()
      onreply(envelope)
    else
      raise RequestTimeout.new(sn)
    end
  end
  
  private

  def onreply(envelope)
    reply = Return.new(envelope)
    if reply.succeeded(envelope)
      return reply.retval()
    else
      raise RemoteException.new(reply.exval())
    end
  end
  
end


class Asynchronous < RequestMethod

  def initialize(producer, tag)
    super(producer)
    @tag = tag
  end
  
  def send(destination, request, any={})
    sn = @producer.send(
      destination,
      :replyto=>replyto(),
      :request=>request,
      :any=>any)
    return sn
  end
  
  def broadcast(destinations, request, any={})
    sns = @producer.send(
      destinations,
      :replyto=>replyto(),
      :request=>request,
      :any=>any)
    return sns
  end
  
  private
  
  def replyto()
    if @tag:
      queue = Gofer::Queue.new(@tag)
      return queue.to_s
    else
      return nil
    end
  end
    
end