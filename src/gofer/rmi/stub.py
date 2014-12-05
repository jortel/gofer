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

from new import classobj
from threading import RLock

from gofer.common import Options, synchronized
from gofer.rmi.policy import Synchronous, Asynchronous
from gofer.rmi.dispatcher import Request


class Builder(object):
    """
    Stub builder.
    """

    def __call__(self, name, url, destination, options):
        """
        Factory method.
        :param name: The stub class (or module) name.
        :type name: str
        :param url: The agent URL.
        :type url: str
        :param destination: The AMQP destination
        :type destination: gofer.messaging.adapter.model.Destination
        :param options: A dict of gofer options
        :param options: Options
        :return: A stub instance.
        :rtype: Stub
        """
        subclass = classobj(name, (Stub,), {})
        inst = subclass(url, destination, options)
        return inst


class Method:
    """
    A dynamic method object used to wrap the RMI call.
    :ivar classname: The target class name.
    :type classname: str
    :ivar name: The target method name.
    :type name: str
    :ivar stub: The stub object used to send the AMQP message.
    :type stub: Stub
    """

    def __init__(self, classname, name, send):
        """
        :param classname: The target class name.
        :type classname: str
        :param name: The target method name.
        :type name: str
        :param send: The function used to send the AMQP message.
        :type send: callable
        """
        self.classname = classname
        self.name = name
        self.send = send

    def __call__(self, *args, **kws):
        """
        Invoke the method .
        :param args: The args.
        :type args: list
        :param kws: The *keyword* arguments.
        :type kws: dict
        """
        opts = Options()
        for k, v in kws.items():
            if k in ('window', 'any',):
                opts[k] = v
                del kws[k]
        request = Request(
            classname=self.classname,
            method=self.name,
            args=args,
            kws=kws)
        return self.send(request, opts)


class Stub:
    """
    The stub class for remote objects.
    All methods mangled because as to not shadow method on the remote.
    :ivar __url: The agent URL.
    :type __url: str
    :ivar __destination: The AMQP destination
    :type __destination: gofer.messaging.adapter.model.Destination
    :ivar __options: Stub options.
    :type __options: Options
    :ivar __mutex: The mutex prevents concurrent calls.
    :type __mutex: RLock
    :ivar __policy: The invocation policy.
    :type __policy: Policy
    """

    def __init__(self, url, destination, options):
        """
        :param url: The agent URL.
        :type url: str
        :param destination: The AMQP destination
        :type destination: str
        :param options: Stub options.
        :type options: Options
        """
        self.__url = url
        self.__destination = destination
        self.__options = Options(options)
        self.__called = (0, None)
        self.__mutex = RLock()
        self.__policy = None

    @synchronized
    def __send(self, request, options):
        """
        Send the request using the configured request method.
        :param request: An RMI request.
        :type request: str
        :param options: Invocation options.
        :type options: Options
        """
        opts = Options(self.__options)
        opts += options
        request.cntr = self.__called[1]
        policy = self.__get_policy()
        if isinstance(self.__destination, (list, tuple)):
            return policy.broadcast(
                self.__destination,
                request,
                window=opts.window,
                secret=opts.secret,
                pam=self.__get_pam(opts),
                any=opts.any)
        else:
            return policy.send(
                self.__destination,
                request,
                window=opts.window,
                secret=opts.secret,
                pam=self.__get_pam(opts),
                any=opts.any)
            
    def __get_pam(self, opts):
        """
        Get PAM options.
        :param opts: options dict.
        :type opts: Options
        :return: pam options
        :rtype: Options
        """
        if opts.user:
            return Options(user=opts.user, password=opts.password)
        else:
            return None

    def __getattr__(self, name):
        """
        Python vodo.
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

    def __call__(self, *args, **options):
        """
        Simulated constructor.
        The 1st call updates stub options.
        The 2nd call updates remote object constructor
        parameters which are passed on RMI calls.
        :param options: keyword options.
        :type options: dict
        :return: self
        :rtype: Stub
        """
        if not self.__called[0]:
            self.__called = (1, None)
            self.__options += options
        else:
            n = self.__called[0]
            self.__called = (n+1, (args, options))
        return self

    def __get_policy(self):
        """
        Get the request policy based on options.
        The policy is cached for performance.
        :return: The request policy.
        :rtype: gofer.rmi.policy.RequestMethod
        """
        if self.__policy is None:
            self.__set_policy()
        return self.__policy
    
    def __set_policy(self):
        """
        Set the request policy based on options.
        """
        if self.__is_asynchronous():
            policy = Asynchronous(self.__url, self.__options)
        else:
            policy = Synchronous(self.__url, self.__options)
        self.__policy = policy

    def __is_asynchronous(self):
        """
        Get whether an *asynchronous* request method
        should be used based on selected options.
        :return: True if async.
        :rtype: bool
        """
        if self.__options.ctag or self.__options.async or self.__options.trigger:
            return True
        return isinstance(self.__destination, (list, tuple))
