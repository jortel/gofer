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
require 'gofer/messaging/policy'
require 'gofer/messaging/stub'
require 'gofer/messaging/producer'


class Agent
end


class Container

  def initialize(uuid, options={})
    url = options.delete(:url)
    @uuid = uuid
    @producer = options.delete(:producer)||Producer.new(nil, url)
    @options = options
  end
  
  def send(name, *args, &block)
    return self.method_missing(name, *args, &block) 
  end

  def method_missing(sym, *args, &block)
    return StubFactory.new(
      sym,
      @uuid,
      @producer,
      @options)
  end

end


class StubFactory
  
  def initialize(cls, uuid, producer, options={})
    @cls = cls
    @id = uuid
    @options = {:window=>{}, :timeout=>90}
    @options.update(options)
    @producer = producer
  end
  
  def new(options={})
    opts = {}
    opts.update(@options)
    opts.update(options)
    opts[:method] = stubmethod(opts)
    destination = destination()
    return Gofer::Stub.new(destination, @cls.to_s, opts)
  end
  
  private
  
  def stubmethod(opts)
    if async()
      ctag = opts[:ctag]
      return Asynchronous.new(@producer, ctag)
    else
      timeout = opts[:timeout]
      return Synchronous.new(@producer, timeout)
    end
  end
  
  def async()
    if ( @options[:ctag] || @options[:async] )
      return true
    end
    return @id.is_a?(Array)
  end
  
  def destination()
    if @id.is_a?(Array)
      queues = []
      @id.each do |d|
        queues << Gofer::Queue.new(d)
      end
      return queues
    else
      return Gofer::Queue.new(@id)
    end
  end
  
end