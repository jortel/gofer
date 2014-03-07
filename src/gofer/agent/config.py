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

import os

from logging import getLogger


from gofer import NAME, Singleton
from gofer.config import Config, Graph
from gofer.config import REQUIRED, OPTIONAL, ANY, BOOL, NUMBER

log = getLogger(__name__)


AGENT_SCHEMA = (
    ('logging', REQUIRED,
        []
    ),
    ('messaging', REQUIRED,
        (
            ('url', OPTIONAL, ANY),
            ('virtual_host', OPTIONAL, ANY),
            ('userid', OPTIONAL, ANY),
            ('password', OPTIONAL, ANY),
            ('cacert', OPTIONAL, ANY),
            ('clientcert', OPTIONAL, ANY),
            ('host_validation', OPTIONAL, BOOL),
            ('transport', OPTIONAL, ANY),
        )
    ),
    ('pam', REQUIRED,
        (
            ('service', OPTIONAL, ANY),
        )
    ),
)


PLUGIN_SCHEMA = (
    ('main', REQUIRED,
        ('enabled', REQUIRED, BOOL),
        ('requires', OPTIONAL, ANY)
    ),
    ('messaging', REQUIRED,
        (
            ('uuid', OPTIONAL, ANY),
            ('url', OPTIONAL, ANY),
            ('virtual_host', OPTIONAL, ANY),
            ('userid', OPTIONAL, ANY),
            ('password', OPTIONAL, ANY),
            ('cacert', OPTIONAL, ANY),
            ('clientcert', OPTIONAL, ANY),
            ('validation', OPTIONAL, BOOL),
            ('transport', OPTIONAL, ANY),
            ('threads', OPTIONAL, NUMBER),
        )
    ),
)


class AgentConfig(Graph):
    """
    The gofer agent configuration.
    :cvar ROOT: The root configuration directory.
    :type ROOT: str
    :cvar PATH: The absolute path to the config directory.
    :type PATH: str
    :cvar USER: The path to an alternate configuration file
        within the user's home.
    :type USER: str
    :cvar ALT: The environment variable with a path to an alternate
        configuration file.
    :type ALT: str
    """
    __metaclass__ = Singleton

    ROOT = '/etc/%s' % NAME
    FILE = 'agent.conf'
    PATH = os.path.join(ROOT, FILE)
    USER = os.path.join('~/.%s' % NAME, FILE)
    CNFD = os.path.join(ROOT, 'conf.d')
    ALT = '%s_OVERRIDE' % NAME.upper()

    def __init__(self):
        """
        Open the configuration.
        Merge (in) alternate configuration file when specified
        by environment variable.
        """
        paths = [self.PATH]
        paths.extend([os.path.join(self.CNFD, n) for n in sorted(os.listdir(self.CNFD))])
        if os.path.exists(self.USER):
            paths.append(self.USER)
        conf = Config(*paths)
        conf.validate(AGENT_SCHEMA)
        Graph.__init__(self, conf)