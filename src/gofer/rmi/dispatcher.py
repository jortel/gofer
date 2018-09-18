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
Provides RMI dispatcher classes.
"""

import sys
import traceback as tb

from gofer import inspection
from gofer.common import Options, new
from gofer.collation import MemberNotFound
from gofer.messaging import Document
from gofer.pam import authenticate as pam_authenticate
from gofer.rmi.model import ALL

from logging import getLogger


log = getLogger(__name__)


# --- Exceptions -------------------------------------------------------------


class DispatchError(Exception):
    pass


class NamespaceNotFound(DispatchError):
    """
    Target namespace not found.
    """

    def __init__(self, name):
        message = '"{}" not provided by plugin.'.format(name)
        DispatchError.__init__(self, message)


class MemberNotFound(DispatchError):
    """
    Target member not found.
    """

    def __init__(self, ns, method):
        message = '"{}.{}()" not provided by plugin.'.format(ns, method)
        DispatchError.__init__(self, message)


class NotAuthorized(DispatchError):
    """
    Not authorized.
    """
    pass


class AuthMethod(NotAuthorized):
    """
    Authentication method not supported.
    """

    def __init__(self, method, name):
        message = '{}(), auth ({}) not supported'.format(method.name, name)
        NotAuthorized.__init__(self, message)


class SecretRequired(NotAuthorized):
    """
    Shared secret required and not passed.
    """

    def __init__(self, method):
        message = '{}(), secret required'.format(method.name)
        NotAuthorized.__init__(self, message)
        
        
class UserRequired(NotAuthorized):
    """
    User (name)  required and not passed.
    """

    def __init__(self, method):
        message = '{}(), user (name) required'.format(method.name)
        NotAuthorized.__init__(self, message)
        
        
class PasswordRequired(NotAuthorized):
    """
    Password required and not passed.
    """

    def __init__(self, method):
        message = '{}(), password required'.format(method.name)
        NotAuthorized.__init__(self, message)


class NotAuthenticated(NotAuthorized):
    """
    PAM authentication failed.
    """

    def __init__(self, method, user):
        message = '{}(), user "{}" not authenticated'.format(method.name, user)
        NotAuthorized.__init__(self, message)
        

class UserNotAuthorized(NotAuthorized):
    """
    The specified user is not authorized to invoke the RMI.
    """

    def __init__(self, method, expected, passed):
        message = \
            '{}(), user must be: {}, passed: {}'.format(
                method.name,
                expected,
                passed)
        NotAuthorized.__init__(self, message)
        

class SecretNotMatched(NotAuthorized):
    """
    Specified secret, not matched.
    """

    def __init__(self, method, expected, passed):
        message = \
            '{}(), secret: {} not in: {}'.format(
                method.name,
                passed,
                expected)
        NotAuthorized.__init__(self, message)
        
        
class RemoteException(Exception):
    """
    The re-raised (propagated) exception base class.
    """

    @staticmethod
    def _import(mod, target):
        """
        Import the concrete exception class.

        Args:
            mod (str): The module name.
            target (str): The class name.

        Returns:
            class: The imported class.
        """
        def _import(m):
            m = __import__(m, fromlist=[str(target)])
            return getattr(m, target)
        try:
            return _import(mod)
        except ImportError:
            return _import(Exception.__module__)

    @staticmethod
    def instance(reply):
        """
        Create an instance of the remote exception.

        Args:
            reply (Document):  The reply.

        Returns:
            Exception: The concrete remote exception.
            RemoteException: When concrete exception cannot be propagated.
        """
        target = reply.xclass
        mod = reply.xmodule
        state = reply.xstate
        args = reply.xargs
        try:
            T = globals().get(target)
            if not T:
                T = RemoteException._import(mod, target)
            try:
                inst = new(T, state)
            except Exception:
                inst = Exception()
            if isinstance(inst, Exception):
                inst.args = args
        except Exception:
            inst = RemoteException(reply.exval)
        return inst
    

# --- RMI Classes ------------------------------------------------------------


class Reply(Document):
    """
    Document for examining replies.
    """

    def succeeded(self):
        """
        Test whether the reply indicates success.
        :return: True when indicates success.
        :rtype: bool
        """
        return self.result and 'retval' in self.result

    def failed(self):
        """
        Test whether the reply indicates failure.
        :return: True when indicates failure.
        :rtype: bool
        """
        return self.result and 'exval' in self.result

    def accepted(self):
        """
        Test whether the reply indicates status (accepted).
        :return: True when indicates started.
        :rtype: bool
        """
        return self.status == 'accepted'

    def rejected(self):
        """
        Test whether the reply indicates status (rejected).
        :return: True when indicates started.
        :rtype: bool
        """
        return self.status == 'rejected'
    
    def started(self):
        """
        Test whether the reply indicates status (started).
        :return: True when indicates started.
        :rtype: bool
        """
        return self.status == 'started'
    
    def progress(self):
        """
        Test whether the reply indicates status (progress).
        :return: True when indicates progress.
        :rtype: bool
        """
        return self.status == 'progress'
    

class Return(Document):
    """
    Return document.
    """

    @classmethod
    def succeed(cls, x):
        """
        Return successful
        :param x: The returned value.
        :type x: any
        :return: A return document.
        :rtype: Return
        """
        inst = Return(retval=x)
        inst.dump()  # validate
        return inst

    @classmethod
    def exception(cls):
        """
        Return raised exception.
        :return: A return document.
        :rtype: Return
        """
        try:
            return cls.__exception()
        except TypeError:
            return cls.__exception()

    def succeeded(self):
        """
        Test whether the return indicates success.
        :return: True when indicates success.
        :rtype: bool
        """
        return 'retval' in self

    def failed(self):
        """
        Test whether the return indicates failure.
        :return: True when indicates failure.
        :rtype: bool
        """
        return 'exval' in self

    @classmethod
    def __exception(cls):
        """
        Return raised exception.
        :return: A return document.
        :rtype: Return
        """
        info = sys.exc_info()
        inst = info[1]
        xclass = inst.__class__
        exval = '\n'.join(tb.format_exception(*info))
        mod = inspection.module(xclass)
        if mod:
            mod = mod.__name__
        args = None
        if issubclass(xclass, Exception):
            args = inst.args
        state = dict(inst.__dict__)
        state['trace'] = exval
        inst = Return(exval=exval,
                      xmodule=mod,
                      xclass=xclass.__name__,
                      xstate=state,
                      xargs=args)
        inst.dump()  # validate
        return inst


class Request(Document):
    """
    An RMI request document.
    """
    pass


class RMI(object):
    """
    The RMI object performs the invocation.
    :ivar request: The request document.
    :type request: Request
    :ivar catalog: A dict of class mappings.
    :type catalog: dict
    """

    def __init__(self, request, auth, catalog):
        """
        :param request: The request document.
        :type request: Request
        :param auth: Authentication properties.
        :type auth: Options
        :param catalog: A dict of class mappings.
        :type catalog: dict
        """
        self.name = '.'.join((request.classname, request.method))
        self.request = request
        self.target = self.find_target(request, catalog)
        self.auth = auth

    @staticmethod
    def find_target(request, catalog):
        """
        Get an instance of the class or module specified in
        the request using the catalog.
        :param request: The request document.
        :type request: Request
        :param catalog: A dict of class mappings.
        :type catalog: dict
        :return: An instance.
        :rtype: (class|module)
        """
        try:
            namespace = catalog[request.classname]
        except KeyError:
            raise NamespaceNotFound(name=request.classname)

        namespace = RMI.construct(request, namespace)

        try:
            target = namespace[request.method]
        except MemberNotFound:
            raise MemberNotFound(
                ns=request.classname,
                method=request.method)

        return target

    @staticmethod
    def construct(request, namespace):
        """
        Construct the namespace using the constructor properties
        in the request.

        Args:
            request (Document): A request.
            namespace (gofer.collation.Container): A class or module.
        """
        cntr = request.cntr
        if not cntr:
            cntr = ([], {})
        return namespace(*cntr[0], **cntr[1])

    def permitted(self):
        """
        Check whether remote invocation of the specified method is permitted.
        Applies security model using Security.
        """
        fninfo = self.target.fninfo
        security = Security(self, fninfo)
        security.apply(self.auth)
        return fninfo

    def __call__(self):
        """
        Invoke the method.
        :return: The invocation result.
        :rtype: Return
        """
        try:
            fninfo = self.permitted()
            model = ALL[fninfo.call.model](
                self.target,
                *self.request.args or [],
                **self.request.kwargs or {})
            retval = model()
            return Return.succeed(retval)
        except Exception:
            log.exception(str(self.target))
            return Return.exception()

    def __str__(self):
        return str(self.request)

    def __repr__(self):
        return str(self.request)


# --- Security classes -------------------------------------------------------


class Security:
    """
    Layered Security.
    :ivar method: The method name.
    :type method: str
    :ivar stack: The security stack; list of auth specifications defined by decorators.
    :type stack: list
    """
    
    def __init__(self, method, fninfo):
        """
        :param method: The method name.
        :type method: RMI
        :param fninfo: The decorated function info.
        :type fninfo: Options
        """
        self.method = method
        self.stack = fninfo.security

    def apply(self, passed):
        """
        Apply auth specifications.
        :param passed: The request's *auth* info passed.
        :type passed: Options.
        :raise SecretRequired: On secret required and not passed.
        :raise SecretNotMatched: On not matched.
        :raise UserRequired: On user required and not passed.
        :raise PasswordRequired: On password required and not passed.
        :raise UserNotAuthorized: On user not authorized.
        :raise NotAuthenticated: On PAM auth failed.
        """
        failed = []
        for name, required in self.stack:
            try:
                fn = self.impl(name)
                return fn(required, passed)
            except NotAuthorized as e:
                log.debug(e)
                failed.append(e)
        if failed:
            raise failed[-1]

    def impl(self, name):
        """
        Find auth implementation by name.
        :param name: auth type (name)
        :type name: str
        :return: The implementation method
        :rtype: instancemethod
        """
        try:
            return getattr(self, name)
        except AttributeError:
            raise AuthMethod(self.method, name)

    def secret(self, required, passed):
        """
        Perform shared secret auth.
        :param required: Method specific auth specification.
        :type required: Options
        :param passed: The credentials passed.
        :type passed: Options
        :raise SecretRequired: On secret required and not passed.
        :raise SecretNotMatched: On not matched.
        """
        secret = required.secret
        if callable(secret):
            secret = secret()
        if not secret:
            return
        if not isinstance(secret, (list, tuple)):
            secret = (secret,)
        if not passed.secret:
            raise SecretRequired(self.method)
        if passed.secret in secret:
            return
        raise SecretNotMatched(self.method, passed.secret, secret)
    
    def pam(self, required, passed):
        """
        Perform PAM authentication.
        :param required: Method specific auth specification.
        :type required: Options
        :param passed: The credentials passed.
        :type passed: Options
        :raise UserRequired: On user required and not passed.
        :raise PasswordRequired: On password required and not passed.
        :raise UserNotAuthorized: On user not authorized.
        :raise NotAuthenticated: On PAM auth failed.
        """
        if passed.pam:
            passed = Options(passed.pam)
        else:
            passed = Options()
        if not passed.user:
            raise UserRequired(self.method)
        if not passed.password:
            raise PasswordRequired(self.method)
        if passed.user != required.user:
            raise UserNotAuthorized(self.method, required.user, passed.user)
        valid = pam_authenticate(passed.user, passed.password, required.service)
        if not valid:
            raise NotAuthenticated(self.method, passed.user)


# --- Dispatcher -------------------------------------------------------------


class Dispatcher:
    """
    The remote invocation dispatcher.
    :ivar catalog: The (catalog) of target classes.
    :type catalog: dict
    """

    @staticmethod
    def auth(document):
        return Options(
            uuid=document.routing[-1],
            secret=document.secret,
            pam=document.pam,)

    @staticmethod
    def log(document):
        request = Options(document.request)
        log.info(
            'call: %s.%s() sn=%s data=%s',
            request.classname,
            request.method,
            document.sn,
            document.data)

    def __init__(self, classes=None):
        """
        :param classes: The (catalog) of target classes and modules.
        :type classes: list
        """
        self.catalog = dict([(c.__name__, c) for c in classes or []])

    def provides(self, name):
        """
        Get whether the name is in the catalog.
        :param name: A class name.
        :type name: str
        :return: True if provides.
        :rtype: bool
        """
        return name in self.catalog

    def dispatch(self, document):
        """
        Dispatch the requested RMI.
        :param document: A request document.
        :type document: Document
        :return: The result.
        :rtype: any
        """
        try:
            self.log(document)
            auth = self.auth(document)
            request = Request(document.request)
            log.debug('request: %s', request)
            method = RMI(request, auth, self.catalog)
            log.debug('method: %s', method)
            return method()
        except Exception:
            log.exception(str(document))
            return Return.exception()

    def __iadd__(self, other):
        if isinstance(other, Dispatcher):
            self.catalog.update(other.catalog)
            return self
        if isinstance(other, list):
            self.catalog.update({c.name: c for c in other})
            return self
        return self

    def __getitem__(self, key):
        return self.catalog[key]

    def __setitem__(self, key, value):
        self.catalog[key] = value

    def __iter__(self):
        _list = []
        for n, v in self.catalog.items():
            if inspection.is_class(v):
                _list.append(v)
                continue
            for fn in inspection.functions(v):
                if RMI.fninfo(fn[1]):
                    _list.append(fn[1])
                continue
        return iter(_list)
