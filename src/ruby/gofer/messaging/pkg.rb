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
require 'uuidtools'
require 'json'
require 'logger'


module Gofer

  VERSION = "0.2"
  
  @@logger = Logger.new('/tmp/ruby-gofer.log')
  
  def Gofer.logger()
    return @@logger
  end
  
  class Destination
    
    def id()
      abstract_method
    end
    
    def address()
      abstract_method    
    end
    
    def create(ssn)
      abstract_method
    end
    
    def delete()
    end
    
  end
  
  
  class Topic < Destination
  
    def initialize(topic, subject="", name="")
      @topic = topic
      @subject = subject
      @name = name
    end
  
  end
  
  
  class Queue < Destination
    
    def initialize(name, durable=false)
      @name = name
      @durable = durable
      @created = false
    end
    
    def id()
      return "queue:#{@name}"    
    end
    
    def address()
      s = ''
      s << @name
      s << ';{'
      s << 'create:always'
      s << ',node:{type:queue,durable:True}'
      s << ',link:{durable:True,x-subscribe:{exclusive:True}}'
      s << '}'
      return s    
    end
  
    def create(ssn)
      # TODO: create as temp when !@durable
      if !@created
        ssn.queue_declare(@name, :exclusive=>true, :auto_delete=>!@durable)
        ssn.exchange_declare(@name, :type=>"direct")
        @created = true
      end
    end
    
    def to_s()
      return @name
    end
    
  end
  
end


def getuuid()
  uuid = UUIDTools::UUID.random_create()
  return uuid.to_s()
end

