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
require 'gofer/messaging/broker'


class Endpoint

  LOCALHOST = "tcp://localhost:5672"
  
  attr_reader :uuid, :url
  
  def initialize(uuid=nil, url=nil)
    @log = Gofer::logger()
    @uuid = uuid||getuuid()
    @url = url||LOCALHOST
    @session = nil
    self.open()
  end
  
  def id()
    return @uuid
  end
  
  def connection()
    broker = Broker.new(@url)
    con = broker.connect()
    @log.info("{#{id}} connected to AMQP")
    return con
  end
  
  def session()
    if @session.nil?
      con = self.connection()
      @session = con.create_session(:name=>@uuid)   
    end
    return @session
  end
  
  def ack()
    begin
      #@session.commit()
    end
  end
  
  def open()
  end
    
  def close()
    if @session == nil
      return
    end
    begin
      @session.close()
      @session = nil
    end
  end
  
  def to_s()
    return 'Endpoint id:%s broker @ %s' % [self.id(), @url]
  end

end