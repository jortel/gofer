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

require 'rubygems'
require 'qpid'
require 'json'
require 'gofer/messaging/pkg'
require 'gofer/messaging/endpoint'


class ReceiverThread
  
  def initialize(consumer)
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
      m = incoming.get(true, nil) # TODO: use 1 instead of nil when supported
      if !m.nil?
        puts "message: \"#{m.body}\" received"
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
    puts "{%s} opening: #{@destination}" % self.id()
    session.message_subscribe(
      :destination => @uuid,
      :queue => @destination.to_s,
      :accept_mode => session.message_accept_mode.none)
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
    envelope = JSON.parse(message.body)
    puts "#{self.id} received:\n#{envelope}"
    if self.valid(envelope)
        self.dispatch(envelope)
    end
    self.ack()
  end
  
  def valid(envelope)
    valid = true
    if envelope['version'] != Gofer::VERSION
        valid = false
        puts "#{self.id} version mismatch (discarded):\n#{envelope}"
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

  def next(timeout=nil)
    m = @incoming.get(true, timeout)
    if !m.nil?
      puts "message: \"#{m.body}\" received"
      envelope = JSON.parse(m.body)
      puts "#{self.id} read next:\n#{envelope}"
      return envelope
    end
  end
  
  def search(sn, timeout)
    puts "#{self.id} searching for: sn=#{sn}"
    while true
      envelope = self.next(timeout)
      if envelope.nil?
        return
      end
      if sn == envelope['sn']
        puts "#{self.id} search found:\n#{envelope}"
        return envelope
      end
      puts "#{self.id} search found:\n#{envelope}"
      self.ack()
    end
  end
    
end
