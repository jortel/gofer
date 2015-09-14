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

from gofer import NAME, Singleton
from gofer.config import Config, Graph
from gofer.config import REQUIRED, OPTIONAL, ANY, BOOL, NUMBER

#
# [management]
#   enabled
#      The manager is (enabled|disabled).
#   host
#      Host (name or IP) the manager listens on.
#   port
#      The port number the manager listens on.
#
# [logging]
#   <module>
#      Logging level
#
# [pam]
#   service
#      The default PAM service for authentication.  Default:passwd
#

AGENT_SCHEMA = (
    ('management', REQUIRED,
        (
            ('enabled', OPTIONAL, BOOL),
            ('host', OPTIONAL, ANY),
            ('port', OPTIONAL, NUMBER),
        )
    ),
    ('logging', REQUIRED,
        []
    ),
    ('pam', REQUIRED,
        (
            ('service', OPTIONAL, ANY),
        )
    ),
)

#
# [main]
#
#   enabled
#      Plugin enabled/disabled (0|1)
#   name
#      The (optional) plugin name. The basename of the descriptor is used when not specified.
#   plugin
#      The (optional) fully qualified module to be loaded from the PYTHON path.
#   threads
#      The (optional) number of threads for the RMI dispatcher.
#   accept
#      Accept forwarding from.  A comma (,) separated list of plugin names (,=none|*=all).
#   forward
#      Forward to.  A comma (,) separated list of plugin names (,=none|*=all).
#
# [messaging]
#
#   uuid
#      The (optional) agent identity. This value also specifies the queue name.
#   url
#      The (optional) broker connection URL.
#   cacert
#      The (optional) SSL CA certificate used to validate the server certificate.
#   clientcert
#      The (optional) SSL client certificate.  PEM encoded and contains both key and certificate.
#   host_validation
#      The (optional) flag indicates SSL host validation should be performed.
#   authenticator
#      The (optional) fully qualified Authenticator to be loaded from the PYTHON path.
#
# [pending]
#
#   depth
#     The pending queue depth.  Default: 10K
#
# [model]
#
#   managed
#      The (optional) level of broker model management.  Default: 2.
#        - 0 = none
#        - 1 = declare and bind queue.
#        - 2 = declare and bind queue; drain and delete queue on explicit detach.
#   queue
#      The (optional) AMQP queue name.  This has precedent over uuid.
#      Format: <exchange>/<queue> where *exchange* is optional.
#   expiration
#      The (optional) auto-deleted queue expiration (seconds).
#

PLUGIN_SCHEMA = (
    ('main', REQUIRED,
        (
            ('enabled', REQUIRED, BOOL),
            ('name', OPTIONAL, ANY),
            ('plugin', OPTIONAL, ANY),
            ('threads', OPTIONAL, NUMBER),
            ('accept', OPTIONAL, ANY),
            ('forward', OPTIONAL, ANY),
        )
    ),
    ('messaging', REQUIRED,
        (
            ('url', OPTIONAL, ANY),
            ('uuid', OPTIONAL, ANY),
            ('cacert', OPTIONAL, ANY),
            ('clientcert', OPTIONAL, ANY),
            ('clientkey', OPTIONAL, ANY),
            ('host_validation', OPTIONAL, BOOL),
            ('authenticator', OPTIONAL, ANY),
            ('heartbeat', OPTIONAL, NUMBER),
        )
    ),
    ('pending', OPTIONAL,
        (
            ('depth', REQUIRED, NUMBER),
        )
    ),
    ('model', OPTIONAL,
        (
            ('managed', OPTIONAL, '(0|1|2)'),
            ('queue', OPTIONAL, ANY),
            ('expiration', OPTIONAL, NUMBER)
        )
    ),
)


AGENT_DEFAULTS = {
    'management': {
        'enabled': '0',
        'host': 'localhost',
        'port': '5650',
    },
    'logging': {
    },
    'pam': {
        'service': 'passwd'
    }
}


PLUGIN_DEFAULTS = {
    'main': {
        'enabled': '0',
        'threads': '1',
        'accept': ',',
        'forward': ','
    },
    'messaging': {
        'heartbeat': '10'
    },
    'pending': {
        'depth': '10000'
    },
    'model': {
        'managed': '2'
    }
}


class AgentConfig(Graph):
    """
    The gofer agent configuration.
    :cvar PATH: The absolute path to the config directory.
    :type PATH: str
    """

    __metaclass__ = Singleton

    PATH = '/etc/%s/agent.conf' % NAME

    def __init__(self, path=None):
        """
        Read the configuration.
        """
        conf = Config(AGENT_DEFAULTS, path or AgentConfig.PATH)
        conf.validate(AGENT_SCHEMA)
        Graph.__init__(self, conf)
