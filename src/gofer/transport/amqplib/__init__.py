# Copyright (c) 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.


from gofer.transport.amqplib.model import Exchange, Queue
from gofer.transport.amqplib.broker import Broker
from gofer.transport.amqplib.consumer import Reader
from gofer.transport.amqplib.producer import Producer, send
from gofer.transport.amqplib.endpoint import Endpoint


PROVIDES = [
    'AMQP-0-8',
    'rabbitmq'
]