#
# Copyright (c) 2015 Red Hat, Inc.
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
from __future__ import print_function


from optparse import OptionParser

from gofer.messaging import Document
from gofer.agent.manager import Client, HOST, PORT


USAGE = '[options]'


parser = OptionParser(description='Management')
parser.add_option('-H', '--host', default=HOST, help='host')
parser.add_option('-p', '--port', default=PORT, type='int', help='port')
parser.add_option('-s', '--show', action='store_true', default=False, help='show loaded plugins')
parser.add_option('-l', '--load', help='load plugin: <path>')
parser.add_option('-r', '--reload', help='reload plugin: <path>')
parser.add_option('-u', '--unload', help='unload plugin: <path>')


def get_options():
    options, _ = parser.parse_args()
    return options


def display(reply):
    if reply.result:
        print(reply.result)


def main():
    options = get_options()
    client = Client(options.host, options.port)
    # show
    if options.show:
        reply = Document(client.show())
        display(reply)
        return reply.code
    # load
    path = options.load
    if path:
        reply = Document(client.load(path))
        display(reply)
        return reply.code
    path = options.reload
    # reload
    if path:
        reply = Document(client.reload(path))
        display(reply)
        return reply.code
    # unload
    path = options.unload
    if path:
        reply = Document(client.unload(path))
        display(reply)
        return reply.code
