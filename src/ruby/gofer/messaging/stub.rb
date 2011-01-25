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
require 'gofer/messaging/dispatcher'

module Gofer

  class Stub
  
    def initialize(pid, classname, opts={})
      @pid = pid
      @classname = classname
      @opts = opts
    end
    
    def send(name, *args, &block)
      return self.method_missing(name, *args, &block) 
    end
  
    def method_missing(sym, *args, &block)
      begin
        puts "invoke: #{@classname}.#{sym}(#{args})"
        request = {
          :classname=>@classname,
          :method=>sym,
          :args=>args,
          :kws=>{}
        }
        return _send(request)
      rescue NoMethodError=>ex
        raise Exception.new("#{ex.name}")
      end
    end
    
    def to_s()
      return "#{@classname} @ '#{@pid}'"
    end
    
    private
  
    def _send(request)
      method = @opts[:method]
      window = @opts[:window]
      window = (window ? window.hash : nil)
      any = @opts[:any]
      if @pid.is_a?(Array)
        return method.broadcast(
          @pid,
          request,
          :window=>window,
          :any=>any)
      else
        return method.send(
          @pid,
          request,
          :window=>window,
          :any=>any)
      end
    end
    
  end

end
