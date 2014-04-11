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
import inspect
import traceback as tb

from gofer import NAME
from gofer.messaging.model import Document, Options
from gofer.pam import PAM

from logging import getLogger


log = getLogger(__name__)


# --- Exceptions -------------------------------------------------------------


class DispatchError(Exception):
    pass


class PluginNotFound(DispatchError):
    """
    Target plugin not found.
    """

    def __init__(self, uuid):
        message = 'plugin for uuid: %s, not found' % uuid
        DispatchError.__init__(self, message)


class ClassNotFound(DispatchError):
    """
    Target class not found.
    """

    def __init__(self, classname):
        DispatchError.__init__(self, classname)


class MethodNotFound(DispatchError):
    """
    Target method not found.
    """

    def __init__(self, classname, method):
        message = '%s.%s(), not found' % (classname, method)
        DispatchError.__init__(self, message)


class NotPermitted(DispatchError):
    """
    Called method not decorated as *remote*.
    """

    def __init__(self, method):
        message = '%s(), not permitted' % method.name
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
        message = \
            '%s(), auth (%s) not supported' % (method.name, name)
        NotAuthorized.__init__(self, message)


class SecretRequired(NotAuthorized):
    """
    Shared secret required and not passed.
    """

    def __init__(self, method):
        message = '%s(), secret required' % method.name
        NotAuthorized.__init__(self, message)
        
        
class UserRequired(NotAuthorized):
    """
    User (name)  required and not passed.
    """

    def __init__(self, method):
        message = '%s(), user (name) required' % method.name
        NotAuthorized.__init__(self, message)
        
        
class PasswordRequired(NotAuthorized):
    """
    Password required and not passed.
    """

    def __init__(self, method):
        message = '%s(), password required' % method.name
        NotAuthorized.__init__(self, message)


class NotAuthenticated(NotAuthorized):
    """
    Not authenticated, user/password failed
    PAM authentication.
    """

    def __init__(self, method, user):
        message = '%s(), user "%s" not authenticated' % (method.name, user)
        NotAuthorized.__init__(self, message)
        

class UserNotAuthorized(NotAuthorized):
    """
    The specified user is not authorized to invoke the RMI.
    """

    def __init__(self, method, expected, passed):
        message = '%s(), user must be: %s, passed: %s' \
            % (method.name,
               expected,
               passed)
        NotAuthorized.__init__(self, message)
        

class SecretNotMatched(NotAuthorized):
    """
    Specified secret, not matched.
    """

    def __init__(self, method, expected, passed):
        message = '%s(), secret: %s not in: %s' \
            % (method.name,
               passed,
               expected)
        NotAuthorized.__init__(self, message)
        
        
class RemoteException(Exception):
    """
    The re-raised (propagated) exception base class.
    """

    @classmethod
    def instance(cls, reply):
        classname = reply.xclass
        mod = reply.xmodule
        state = reply.xstate
        args = reply.xargs
        try:
            C = globals().get(classname)
            if not C:
                mod = __import__(mod, {}, {}, [classname,])
                C = getattr(mod, classname)
            inst = cls.__new(C)
            inst.__dict__.update(state)
            if isinstance(inst, Exception):
                inst.args = args
        except:
            inst = RemoteException(reply.exval)
        return inst
    
    @classmethod
    def __new(cls, C):
        try:
            import new
            return new.instance(C)
        except:
            pass
        return Exception.__new__(C)
    

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
        mod = inspect.getmodule(xclass)
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
        self.auth = auth
        self.inst = self.find_class(request, catalog)
        self.method = self.find_method(request, self.inst)
        self.args = request.args
        self.kwargs = request.kws

    @staticmethod
    def find_class(request, catalog):
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
        key = request.classname
        inst = catalog.get(key, None)
        if inst is None:
            raise ClassNotFound(key)
        if inspect.isclass(inst):
            args, keywords = RMI.constructor(request)
            return inst(*args, **keywords)
        else:
            return inst

    @staticmethod
    def find_method(request, inst):
        """
        Get method of the class specified in the request.
        Ensures that remote invocation is permitted.
        :param request: The request document.
        :type request: Request
        :param inst: A class or module object.
        :type inst: (class|module)
        :return: The requested method.
        :rtype: (method|function)
        """
        cn, fn = (request.classname, request.method)
        if hasattr(inst, fn):
            return getattr(inst, fn)
        else:
            raise MethodNotFound(cn, fn)

    @staticmethod
    def fn(method):
        """
        Return the method's function (if a method) or
        the *method* assuming it's a function.
        :param method: An instance method.
        :type method: instancemethod
        :return: The function
        :rtype: function
        """
        if inspect.ismethod(method):
            fn = method.im_func
        else:
            fn = method
        return fn

    @staticmethod
    def fninfo(method):
        """
        Get the *gofer* metadata embedded in the function
        by the @remote decorator.
        :param method: An instance method.
        :type method: instancemethod
        :return: The *gofer* attribute.
        :rtype: Options
        """
        try:
            return getattr(RMI.fn(method), NAME)
        except:
            pass

    @staticmethod
    def constructor(request):
        """
        Get (optional) constructor arguments.
        :return: cntr: ([],{})
        """
        cntr = request.cntr
        if not cntr:
            cntr = ([], {})
        return cntr

    def permitted(self):
        """
        Check whether remote invocation of the specified method is permitted.
        Applies security model using Security.
        """
        fninfo = RMI.fninfo(self.method)
        if fninfo is None:
            raise NotPermitted(self)
        security = Security(self, fninfo)
        security.apply(self.auth)

    def __call__(self):
        """
        Invoke the method.
        :return: The invocation result.
        :rtype: Return
        """
        try:
            self.permitted()
            retval = self.method(*self.args, **self.kwargs)
            return Return.succeed(retval)
        except Exception:
            log.exception(str(self.method))
            return Return.exception()

    def __str__(self):
        return str(self.request)

    def __repr__(self):
        return str(self)


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
        :type method: str
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
            except NotAuthorized, e:
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
        pam = PAM()
        try:
            pam.authenticate(passed.user, passed.password, required.service)
        except Exception:
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
            'call: %s.%s() sn=%s info=%s',
            request.classname,
            request.method,
            document.sn,
            document.any)

    def __init__(self, classes=None):
        """
        :param classes: The (cataloged) of target classes.
        :type classes: list
        """
        self.catalog = dict([(c.__name__, c) for c in classes or []])

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
            other = dict([(c.__name__, c) for c in other])
            self.catalog.update(other)
            return self
        return self

    def __getitem__(self, key):
        return self.catalog[key]

    def __setitem__(self, key, value):
        self.catalog[key] = value

    def __iter__(self):
        _list = []
        for n, v in self.catalog.items():
            if inspect.isclass(v):
                _list.append(v)
                continue
            for fn in inspect.getmembers(v, inspect.isfunction):
                if RMI.fninfo(fn[1]):
                    _list.append(fn[1])
                continue
        return iter(_list)