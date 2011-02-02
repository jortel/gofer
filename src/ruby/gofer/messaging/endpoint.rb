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
  
  def session
    if @session.nil?
      con = self.connection()
      @session = con.session(@uuid)      
    end
    return @session
  end
  
  def ack()
    begin
      #@session.ack()
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