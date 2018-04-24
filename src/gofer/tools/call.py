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


import sys

from optparse import OptionParser
from logging import basicConfig, CRITICAL

from gofer.compat import str, json
from gofer.messaging import Connection
from gofer.messaging.adapter.model import DEFAULT_URL
from gofer.proxy import Agent


USAGE = '[options] [<argument>... [<keyword>=<value>...]'


parser = OptionParser(description='Remote method invocation')
parser.add_option('-u', '--url', default=DEFAULT_URL, help='url')
parser.add_option('-a', '--address', help='agent (amqp) address')
parser.add_option('-r', '--reply', help='reply (amqp) address')
parser.add_option('-t', '--target', help='RMI target')
parser.add_option('-i', '--input', help='RMI input (json) document')
parser.add_option('-w', '--wait', help='seconds to wait for a synchronous reply')
parser.add_option('-p', '--progress', help='progress prefix')
parser.add_option('-d', '--data', help='user (json) data')
parser.add_option('-S', '--secret', help='shared secret')
parser.add_option('-T', '--ttl', help='shared secret')
parser.add_option('-A', '--authenticator', help='authenticator python package')
parser.add_option('-U', '--user', help='user')
parser.add_option('-P', '--password', help='password')


def cast(value):
    try:
        return int(value)
    except ValueError:
        pass
    return value


def get_parameters(passed):
    keywords = {}
    arguments = []
    for argument in passed:
        parts = argument.split('=', 1)
        if len(parts) == 2:
            keywords[parts[0]] = cast(parts[1])
        else:
            arguments.append(cast(parts[0]))
    return tuple(arguments), keywords


def get_options():
    options, arguments = parser.parse_args()
    parameters = get_parameters(arguments)
    return options, parameters[0], parameters[1]


def validate(options):
    if not options.address:
        print('Address must be specified')
        parser.print_help()
        sys.exit(1)
    if not options.target:
        print('Target must be specified')
        parser.print_help()
        sys.exit(1)
    if '.' not in options.target:
        print('Target must be: <class>.<method>')
        parser.print_help()
        sys.exit(1)
    if options.ttl:
        try:
            int(options.ttl)
        except ValueError:
            print('TTL must be <int>')
            parser.print_help()
            sys.exit(1)
    if options.wait:
        try:
            int(options.wait)
        except ValueError:
            print('Wait must be <int>')
            parser.print_help()
            sys.exit(1)
    if options.data:
        try:
            json.loads(options.data)
        except ValueError:
            print('data must be valid json')
            parser.print_help()
            sys.exit(1)
    if options.input:
        try:
            document = json.loads(options.input)
            if not isinstance(document, list):
                raise ValueError()
            if len(document) != 2:
                raise ValueError()
            if not isinstance(document[0], list):
                raise ValueError()
            if not isinstance(document[1], dict):
                raise ValueError()
        except ValueError as e:
            print(str(e))
            print('Input must be valid json: [[], {}]')
            parser.print_help()
            sys.exit(1)


def main():
    g_opt = {}
    options, arguments, keywords = get_options()
    basicConfig(level=CRITICAL)
    validate(options)

    if options.ttl:
        g_opt['ttl'] = int(options.ttl)
    if options.wait:
        g_opt['wait'] = int(options.wait)
    if options.progress:
        def print_report(report):
            print(''.join((options.progress, str(report['details']))))
        g_opt['progress'] = print_report
    if options.data:
        g_opt['data'] = json.loads(options.data)
    if options.secret:
        g_opt['secret'] = options.secret
    if options.authenticator:
        parts = options.authenticator.split('.')
        path = '.'.join(parts[:-1])
        name = parts[-1]
        mod = __import__(path, {}, {}, [name])
        g_opt['authenticator'] = getattr(mod, name)()
    if options.user:
        g_opt['user'] = options.user
    if options.password:
        g_opt['password'] = options.password
    if options.reply:
        g_opt['reply'] = options.reply
    if options.input:
        document = json.loads(options.input)
        arguments = tuple(document[0])
        keywords = document[1]

    with Connection(options.url, retry=False):
        agent = Agent(options.url, options.address, **g_opt)
        target = options.target.split('.', 1)
        stub = getattr(agent, target[0])
        method = getattr(stub, target[1])
        retval = method(*arguments, **keywords)
        print(retval)
