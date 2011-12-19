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

require 'gofer/rmi/dispatcher'
require 'gofer/messaging/pkg'
require 'gofer/messaging/consumer'

class RequestTimeout < Exception ; end


class RequestMethod

  def initialize(producer)
    @log = Gofer::logger()
    @producer = producer    
  end
  
  def send(address, request, any={})
    abstract_method
  end
  
  def broadcast(addresses, request, any={}) ; end
  
  def close()
    @producer.close()
  end
  
  def timeout(options, none=[nil,nil])
    tm = options[:timeout]
    if tm.nil?
      return none
    end
    return tm.is_a?(Array) ? tm : [tm, tm]
  end

end


class Synchronous < RequestMethod
  
  @@TIMEOUT = [10,90]
  
  def initialize(producer, options)
    super(producer)
    @timeout = timeout(options, @@TIMEOUT)
    @queue = Gofer::Queue.new(getuuid(), false)
    @reader = Reader.new(@queue, nil, producer.url)
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
      if envelope[:status]
        @log.info("request (#{sn}), started")
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

  def initialize(producer, options)
    super(producer)
    @timeout = timeout(options)
    @tag = options[:ctag]
  end
  
  def send(destination, request, options={})
    body = {
      :replyto=>replyto(),
      :request=>request,
    }
    body.update(options)
    ttl = @timeout[0]
    sn = @producer.send(destination, body, ttl=ttl)
    return sn
  end
  
  def broadcast(destinations, request, options={})
    body = {
      :replyto=>replyto(),
      :request=>request,
    }
    body.update(options)
    ttl = @timeout[0]
    sns = @producer.send(destinations, body, ttl)
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