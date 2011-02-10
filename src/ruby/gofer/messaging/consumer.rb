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

require 'pp'
require 'timeout'
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
      incoming = @consumer.incoming()
      begin
        Timeout::timeout(1) do
          m = incoming.get(true)
          @log.info("message: \"#{m.body}\" received")
          @consumer.received(m)
        end
      rescue Timeout::Error ;
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
    @incoming = nil
    @destination = destination
    super(uuid, url)
  end
  
  def id()
    return @destination.id()    
  end
  
  def open()
    session = self.session()
    @destination.create(session)
    @log.info("{#{self.id}} opening: #{@destination}")
    session.message_subscribe(
      :destination=>@uuid,
      :queue=>@destination.to_s,
      :accept_mode=>session.message_accept_mode.none)
    @incoming = session.incoming(@uuid)
  end
  
  def start()
    @incoming.start()
    @thread = ReceiverThread.new(self)
    @thread.start()    
  end
  
  def stop()
    begin
      @incoming.stop()
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


class Reader < Consumer

  def start()
    @incoming.start()
  end

  def stop()
    begin
      @incoming.stop()
    end
  end

  def next(timeout=0)
    begin
      Timeout::timeout(timeout) do
        m = @incoming.get(true)
        @log.info("message: \"#{m.body}\" received")
        envelope = JSON.parse(m.body, :symbolize_names=>true)
        @log.debug("#{self.id} read next:\n#{envelope.inspect}")
        return envelope
      end
    rescue Timeout::Error ;
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
    
end
