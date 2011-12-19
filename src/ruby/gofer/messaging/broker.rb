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

require 'rubygems'
require 'qpid'

class Broker

  @@domain = {}

  def Broker.new(url)
    broker = @@domain[url]
    if broker.nil?
      broker = self.allocate()
      broker.send(:initialize, url)
      @@domain[url] = broker
    end
    return broker
  end
  
  def initialize(url)
    if url.instance_of?(URL)
      @url = url
    else
      @url = URL.new(url)
    end
    @cacert = nil
    @clientcert = nil
    @connection = nil
  end
  
  def id()
    return @url.simple()
  end
  
  def connect()
    if @connection.nil?
      @connection = Qpid::Messaging::Connection.new(:url=>@url.to_s)
      @connection.open()
    end
    return @connection
  end
  
  def close()
    begin
      @conection.stop()
      @connection = nil
    rescue
    end
  end
  
end


class URL
  
  attr_reader :transport, :host, :port

  def URL.split(s)
    t = Struct.new(:transport, :host, :port)
    d = t.new()
    s1 = URL.spliturl(s)
    d.transport = s1.transport
    s2 = URL.splitport(s1.hp)
    d.host = s2.host
    d.port = s2.port
    return d
  end
  
  def URL.spliturl(s)
    t = Struct.new(:transport, :hp)
    d = t.new()
    part = s.split('://', 2)
    if part.length > 1
      d.transport = part[0]
      d.hp = part[1]
    else
      d.transport = 'tcp'
      d.hp = part[0]
    end
    return d
  end
  
  def URL.splitport(s, dp=5672)
    t = Struct.new(:host, :port)
    d = t.new()
    part = s.split(':', 2)
    if part.length > 1
      d.host = part[0]
      d.port = part[1]
    else
      d.host = part[0]
      d.port = dp
    end
    return d
  end
 
  def initialize(s)
    s1 = URL.split(s)
    @transport = s1.transport
    @host = s1.host
    @port = s1.port
  end

  def simple
    return '%s:%d' % [@host, @port]    
  end
  
  def hash
    return self.simple().hash()    
  end
  
  def eql(other)
    return self.simple() == other.simple()    
  end
  
  def ==(other)
    return self.eql(other)    
  end
  
  def to_s()
    return '%s:%s:%d' %
      [@transport,
       @host,
       @port]    
  end
  
end