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
require 'rubygems'
require 'qpid'
require 'json'
require 'gofer/messaging/pkg'
require 'gofer/messaging/endpoint'


class Producer < Endpoint
  
  def open ; end
    
  def send(destination, body={}, ttl=nil)
    sn = getuuid()
    ssn = self.session()
    envelope = {
        :sn=>sn,
        :version=>Gofer::VERSION,
        :origin=>self.id()
    }
    envelope.update(body)
    json = JSON.pretty_generate(envelope)
    address = destination.to_s()
    dp = ssn.delivery_properties(:routing_key=>address, :ttl=>ttl)
    mp = ssn.message_properties(:content_type=>"text/plain")
    msg = Qpid::Message.new(dp, mp, json)
    ssn.message_transfer(:message=>msg)
    @log.info("#{self.id} sent (#{address})\n#{envelope.inspect}")
    return sn
  end
  
  def broadcast(destinations, body={})
    sns = []
    item = Struct.new(:uuid, :sn)
    destinations.each do |dst|
      sn = self.send(dst, body)
      sns << item.new(dst.to_s, sn)
    end
    return sns
  end

end