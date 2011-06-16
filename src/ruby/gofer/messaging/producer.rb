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
    unless ttl.nil?
      ttl = ttl*1000
    end
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