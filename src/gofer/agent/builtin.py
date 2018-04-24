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

from gofer import inspection
from gofer import collation
from gofer.agent.decorator import Actions
from gofer.agent.reporting import loaded
from gofer.decorators import options
from gofer.rmi.tracker import Tracker
from gofer.rmi.criteria import Builder
from gofer.rmi.dispatcher import Dispatcher
from gofer.threadpool import ThreadPool


def remote(fn):
    """
    Minimum needed for remote invocation.
    """
    options(fn)
    return fn


class Admin(object):
    """
    Provides administration.
    """

    container = None

    @remote
    def cancel(self, sn=None, criteria=None):
        """
        Cancel by serial number or user defined property.
        :param sn: An RMI serial number.
        :type sn: str
        :param criteria: The criteria used to match the
            *data* property on an RMI request.
        :type criteria: dict
        :return: The list of cancelled serial numbers.
        :rtype: list
        :raise Exception, on (sn) not found.
        :see: gofer.rmi.criteria
        """
        sn_list = []
        cancelled = []
        tracker = Tracker()
        if sn:
            sn_list = [sn]
        if criteria:
            b = Builder()
            criteria = b.build(criteria)
            sn_list = tracker.find(criteria)
        for sn in sn_list:
            _sn = tracker.cancel(sn)
            if _sn:
                cancelled.append(_sn)
        return cancelled

    @remote
    def echo(self, text):
        """
        Echo the specified text.
        :param text: Any text.
        :type text: str
        :return: The specified text.
        :rtype: str
        """
        return text

    @remote
    def hello(self):
        """
        Get hello message.
        :return: The message.
        :rtype: str
        """
        return 'Hello, I am gofer agent'

    @remote
    def help(self):
        """
        Show information about loaded plugins.
        :return: Information
        :rtype: str
        """
        return loaded(self.container, Actions())

    @property
    def __name__(self):
        return self.__class__.__name__

    def __call__(self):
        return self


class Builtin(object):
    """
    The builtin pseudo-plugin.
    """

    @staticmethod
    def _dispatcher():
        collator = collation.Collator()
        classes, _ = collator({f[1]: {} for f in inspection.methods(Admin)})
        dispatcher = Dispatcher()
        dispatcher += classes
        return dispatcher

    def __init__(self, plugin):
        """
        :param plugin: A real plugin.
        :type plugin: gofer.agent.plugin.Plugin
        """
        Admin.container = plugin.container
        self.pool = ThreadPool(3)
        self.dispatcher = self._dispatcher()
        self.plugin = plugin
        self.latency = 0

    @property
    def url(self):
        return self.plugin.url

    @property
    def authenticator(self):
        return self.plugin.authenticator

    def provides(self, name):
        """
        Get whether the plugin provides the name.
        :param name: A class name.
        :type name: str
        :return: True if provides.
        :raise: bool
        """
        return self.dispatcher.provides(name)

    def dispatch(self, request):
        """
        Dispatch (invoke) the specified RMI request.
        :param request: An RMI request
        :type request: gofer.Document
        :return: The RMI returned.
        """
        return self.dispatcher.dispatch(request)

    def start(self):
        """
        Start the plugin.
        """
        self.pool.start()

    def shutdown(self):
        """
        Shutdown the plugin.
        """
        self.pool.shutdown()
