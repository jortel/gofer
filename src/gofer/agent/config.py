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


AGENT_SCHEMA = (
    ('logging', REQUIRED,
        []
    ),
    ('pam', REQUIRED,
        (
            ('service', OPTIONAL, ANY),
        )
    ),
)


PLUGIN_SCHEMA = (
    ('main', REQUIRED,
        (
            ('enabled', REQUIRED, BOOL),
            ('requires', OPTIONAL, ANY),
            ('extends', OPTIONAL, ANY)
        )
    ),
    ('messaging', REQUIRED,
        (
            ('url', OPTIONAL, ANY),
            ('uuid', OPTIONAL, ANY),
            ('cacert', OPTIONAL, ANY),
            ('clientcert', OPTIONAL, ANY),
            ('host_validation', OPTIONAL, BOOL),
            ('threads', OPTIONAL, NUMBER),
        )
    ),
    ('model', OPTIONAL,
        (
            ('managed', OPTIONAL, '(0|1|2)'),
            ('queue', OPTIONAL, ANY),
            ('exchange', OPTIONAL, ANY),
            ('expiration', OPTIONAL, NUMBER)
        )
    ),
)


PLUGIN_DEFAULTS = {
    'main': {
        'enabled': '0',
    },
    'messaging': {
        'threads': '1',
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

    def __init__(self, path=PATH):
        """
        Read the configuration.
        """
        conf = Config(path)
        conf.validate(AGENT_SCHEMA)
        Graph.__init__(self, conf)
