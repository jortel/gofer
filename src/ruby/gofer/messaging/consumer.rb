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

require 'pp'
require 'rubygems'
require 'qpid'
require 'json'
require 'gofer/messaging/pkg'
require 'gofer/messaging/endpoint'


class ReceiverThread
  
  def initialize(consumer)
    @log = Gofer::logger()
    @consumer = consumer
    @thread = nil
  end
  
  def start()
    @thread = Thread.new{self.run()}
  end
  
  def stop()
    @consumer.close()
    @thread.kill()  
  end
  
  def run()
    while true
      receiver = @consumer.receiver()
      timeout = Qpid::Messaging::Duration.new(1000)
      m = receiver.fetch(10)
      unless m.nil?
        @log.info("message: \"#{m.body}\" received")
        @consumer.received(m)
      end
    end
  end
  
  def join(wait=10)
    @thread.join(wait)    
  end
  
end


class Consumer < Endpoint
  
  attr_reader :incoming
  
  def initialize(destination, uuid=nil, url=nil)
    @thread = nil
    @receiver = nil
    @destination = destination
    super(uuid, url)
  end
  
  def id()
    return @destination.id()    
  end
  
  def open()
    session = self.session()
    @log.info("{#{self.id}} opening: #{@destination}")
    @receiver = session.create_receiver(@destination.to_s)
  end
  
  def start()
    @thread = ReceiverThread.new(self)
    @thread.start()    
  end
  
  def stop()
    begin
      @thread.stop()
      @thread.join(90)
    end
  end
  
  def close()
    self.close()
    @receiver.close()
  end
  
  def join(wait=10)
    @thread.join(wait)
  end
  
  def received(message)
    envelope = JSON.parse(message.body, :symbolize_names=>true)
    @log.info("#{self.id} received:\n#{envelope.inspect}")
    if self.valid(envelope)
        self.dispatch(envelope)
    end
    self.ack()
  end
  
  def valid(envelope)
    valid = true
    if envelope[:version] != Gofer::VERSION
        valid = false
        @log.info("#{self.id} version mismatch (discarded):\n#{envelope.inspect}")
    end
    return valid
  end
  
  def dispatch(envelope) ; end

end


class Reader < Endpoint
  
  def initialize(destination, uuid=nil, url=nil)
    super(uuid, url)
    session = self.session()
    @receiver = session.create_receiver(destination.to_s)
  end

  def next(timeout=0)
    duration = Qpid::Messaging::Duration.new(timeout*1000)
    m = @receiver.fetch(duration)
    unless m.nil?
      @log.info("message: \"#{m.content}\" received")
      envelope = JSON.parse(m.content, :symbolize_names=>true)
      @log.debug("#{self.id} read next:\n#{envelope.inspect}")
      return envelope
    end
  end
  
  def search(sn, timeout)
    @log.debug("#{self.id} searching for: sn=#{sn}")
    while true
      envelope = self.next(timeout)
      if envelope.nil?
        return
      end
      if sn == envelope[:sn]
        @log.debug("#{self.id} search found:\n#{envelope.inspect}")
        return envelope
      end
      @log.debug("#{self.id} search found:\n#{envelope.inspect}")
      self.ack()
    end
  end
  
  def close()
    @receiver.close()
  end
    
end
