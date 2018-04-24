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

"""
Contains stub classes.
Proxies (stubs) are the *local* representation of *remote*
classes on which we invoke methods.
"""

from threading import RLock

from gofer.common import Options, newT, synchronized
from gofer.rmi.policy import Policy
from gofer.rmi.dispatcher import Request


class Builder(object):
    """
    Stub builder.
    """

    def __call__(self, name, url, address, options):
        """
        Factory method.
        :param name: The stub class (or module) name.
        :type name: str
        :param url: The agent URL.
        :type url: str
        :param address: The AMQP address
        :type address: str
        :param options: A dict of gofer options
        :param options: Options
        :return: A stub instance.
        :rtype: Stub
        """
        T = newT(name, (Stub,))
        inst = T(url, address, options)
        return inst


class Method:
    """
    A dynamic method object used to wrap the RMI call.
    :ivar cn: The target class name.
    :type cn: str
    :ivar name: The target method name.
    :type name: str
    :ivar send: The method used to send the AMQP message.
    :type send: Stub
    """

    def __init__(self, cn, name, send):
        """
        :param cn: The class name.
        :type cn: str
        :param name: The target method name.
        :type name: str
        :param send: The function used to send the AMQP message.
        :type send: callable
        """
        self.cn = cn
        self.name = name
        self.send = send

    def __call__(self, *args, **keywords):
        """
        Invoke the method .
        :param args: The args.
        :type args: list
        :param kws: The *keyword* arguments.
        :type kws: dict
        """
        request = Request(
            classname=self.cn,
            method=self.name,
            args=args,
            kws=keywords)
        return self.send(request)


class Stub:
    """
    The stub class for remote objects.
    All methods mangled because as to not shadow method on the remote.
    :ivar __url: The agent URL.
    :type __url: str
    :ivar __address: The AMQP address
    :type __address: str
    :ivar __mutex: The mutex prevents concurrent calls.
    :type __mutex: RLock
    :ivar __policy: The invocation policy.
    :type __policy: Policy
    :ivar __cntr: The constructor arguments.
    :type __cntr: tuple
    """

    def __init__(self, url, address, options):
        """
        :param url: The agent URL.
        :type url: str
        :param address: The AMQP address
        :type address: str
        :param options: Stub options.
        :type options: Options
        """
        self.__url = url
        self.__address = address
        self.__mutex = RLock()
        self.__policy = Policy(url, address, options)
        self.__cntr = None

    @synchronized
    def __send(self, request):
        """
        Send the request using the configured request method.
        :param request: An RMI request.
        :type request: str
        """
        request.cntr = self.__cntr
        return self.__policy(request)

    def __getattr__(self, name):
        """
        Python magic.
        Get a *Method* object for any requested attribute.
        :param name: The attribute name.
        :type name: str
        :return: A method object.
        :rtype: Method
        """
        if name.startswith('_'):
            raise AttributeError('protected')
        cn = self.__class__.__name__
        return Method(cn, name, self.__send)
    
    def __getitem__(self, name):
        """
        Python magic.
        Get a *Method* object for any requested attribute.
        :param name: The attribute name.
        :type name: str
        :return: A method object.
        :rtype: Method
        """
        return getattr(self, name)

    def __call__(self, *args, **keywords):
        """
        Simulated constructor.
        :param options: keyword options.
        :type options: dict
        """
        self.__cntr = (args, keywords)
        return self
