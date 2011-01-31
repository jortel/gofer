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
require 'gofer/messaging/policy'
require 'gofer/messaging/stub'


class Agent
end


class Container

  def initialize(uuid, options={})
    @uuid = uuid
    @producer = options.delete(:producer)
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