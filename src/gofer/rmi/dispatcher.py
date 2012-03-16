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
from gofer.messaging import *
from gofer.pam import PAM
from logging import getLogger


log = getLogger(__name__)

#
# Exceptions
#

class DispatchError(Exception):
    pass


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
    Called method not decorated as I{remote}.
    """

    def __init__(self, cnfn):
        message = '%s.%s(), not permitted' % cnfn
        DispatchError.__init__(self, message)
        
        
class NotAuthorized(DispatchError):
    """
    Not authorized.
    """
    pass


class AuthMethod(DispatchError):
    """
    Authentication method not supported.
    """

    def __init__(self, cnfn, name):
        message = \
            '%s.%s(), auth (%s) not supported' % \
            (cnfn[0],
             cnfn[1],
             name)
        NotAuthorized.__init__(self, message)
        
        
class NotShared(NotAuthorized):
    """
    Method not shared between UUIDs.
    """

    def __init__(self, cnfn):
        message = '%s.%s(), not shared' % cnfn
        DispatchError.__init__(self, message)


class SecretRequired(NotAuthorized):
    """
    Shared secret required and not passed.
    """

    def __init__(self, cnfn):
        message = '%s.%s(), secret required' % cnfn
        NotAuthorized.__init__(self, message)
        
        
class UserRequired(NotAuthorized):
    """
    User (name)  required and not passed.
    """

    def __init__(self, cnfn):
        message = '%s.%s(), user (name) required' % cnfn
        NotAuthorized.__init__(self, message)
        
        
class PasswordRequired(NotAuthorized):
    """
    Password required and not passed.
    """

    def __init__(self, cnfn):
        message = '%s.%s(), password required' % cnfn
        NotAuthorized.__init__(self, message)


class NotAuthenticated(NotAuthorized):
    """
    Not authenticated, user/password failed
    PAM authentication.
    """

    def __init__(self, cnfn, user):
        message = '%s.%s(), user "%s" not authenticted'\
            % (cnfn[0], cnfn[1], user)
        NotAuthorized.__init__(self, message)
        

class UserNotAuthorized(NotAuthorized):
    """
    The specified user is not authorized to invoke the RMI.
    """

    def __init__(self, cnfn, expected, passed):
        message = '%s.%s(), user must be: %s, passed: %s'\
            % (cnfn[0],
               cnfn[1],
               expected,
               passed)
        NotAuthorized.__init__(self, message)
        

class SecretNotMatched(NotAuthorized):
    """
    Specified secret, not matched.
    """

    def __init__(self, cnfn, expected, passed):
        message = '%s.%s(), secret: %s not in: %s' \
            % (cnfn[0],
               cnfn[1],
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
    

#
# RMI Classes
#

class Return(Envelope):
    """
    Return envelope.
    """

    @classmethod
    def succeed(cls, x):
        """
        Return successful
        @param x: The returned value.
        @type x: any
        @return: A return envelope.
        @rtype: L{Return}
        """
        inst = Return(retval=x)
        inst.dump() # validate
        return inst

    @classmethod
    def exception(cls):
        """
        Return raised exception.
        @return: A return envelope.
        @rtype: L{Return}
        """
        try:
            return cls.__exception()
        except TypeError:
            return cls.__exception()

    def succeeded(self):
        """
        Test whether the return indicates success.
        @return: True when indicates success.
        @rtype: bool
        """
        return ( 'retval' in self )

    def failed(self):
        """
        Test whether the return indicates failure.
        @return: True when indicates failure.
        @rtype: bool
        """
        return ( not self.succeeded() )
    
    @classmethod
    def __exception(cls):
        """
        Return raised exception.
        @return: A return envelope.
        @rtype: L{Return}
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
        inst.dump() # validate
        return inst


class Request(Envelope):
    """
    An RMI request envelope.
    """
    pass


class RMI(object):
    """
    The RMI object performs the invocation.
    @ivar request: The request envelope.
    @type request: L{Request}
    @ivar catalog: A dict of class mappings.
    @type catalog: dict
    """

    def __init__(self, request, catalog):
        """
        @param request: The request envelope.
        @type request: L{Request}
        @param catalog: A dict of class mappings.
        @type catalog: dict
        """
        self.request = request
        self.catalog = catalog

    def resolve(self):
        """
        Resolve the class/method in the request.
        @return: A tuple (inst, method)
        @rtype: tuple
        """
        inst = self.getclass()
        method = self.getmethod(inst)
        return (inst, method)

    def getclass(self):
        """
        Get an instance of the class or module specified in
        the request using the catalog.
        @return: An instance.
        @rtype: (class|module)
        """
        key = self.request.classname
        inst = self.catalog.get(key, None)
        if inst is None:
            raise ClassNotFound(key)
        if inspect.isclass(inst):
            args,keywords = self.__constructor()
            return inst(*args, **keywords)
        else:
            return inst

    def getmethod(self, inst):
        """
        Get method of the class specified in the request.
        Ensures that remote invocation is permitted.
        @param inst: A class or module object.
        @type inst: (class|module)
        @return: The requested method.
        @rtype: (method|function)
        """
        cn, fn = self.cnfn()
        if hasattr(inst, fn):
            method = getattr(inst, fn)
            return self.permitted(method)
        else:
            raise MethodNotFound(cn, fn)
        
    def permitted(self, method):
        """
        Check whether remote invocation of the specified method is permitted.
        Applies security model using L{Security}.
        @param method: The method in question.
        @type method: (method|function)
        @return: True if permitted.
        @rtype: bool
        """
        auth = self.request.auth
        fninfo = self.__fninfo(method)
        if fninfo is None:
            raise NotPermitted(self.cnfn())
        self.__shared(fninfo, auth)
        security = Security(self, fninfo)
        security.apply(auth)
        return method
    
    def cnfn(self):
        """
        Get the I{classname} and I{function} specified in the request.
        @return: (classname, function-name)
        @rtype: tuple
        """
        return (self.request.classname,
                self.request.method)
        
    def __shared(self, fninfo, auth):
        """
        Validate the method is either marked as I{shared}
        or that the request was received on the method's
        contributing plugin UUID.
        @param fninfo: The decorated function info.
        @type fninfo: L{Options}
        @param auth: The request's I{auth} info.
        @type auth: L{Options}
        @raise NotShared: On sharing violation.
        """
        if fninfo.shared:
            return
        uuid = fninfo.plugin.getuuid()
        if not uuid:
            return
        log.debug('match uuid: "%s" = "%s"', auth.uuid, uuid)
        if auth.uuid == uuid:
            return
        raise NotShared(self.cnfn())

    def __fn(self, method):
        """
        Return the method's function (if a method) or
        the I{method} assuming it's a function.
        @return: The function
        @rtype: function
        """
        if inspect.ismethod(method):
            fn = method.im_func
        else:
            fn = method
        return fn
    
    def __fninfo(self, method):
        """
        Get the I{gofer} metadata embedded in the function
        by the @remote decorator.
        @param method: A called (resolved) method
        @type method: function
        @return: The I{gofer} attribute.
        @rtype: L{Options}
        """
        try:
            return getattr(self.__fn(method), NAME)
        except:
            pass
        
    def __constructor(self):
        """
        Get (optional) constructor arguments.
        @return: cntr: ([],{})
        """
        cntr = self.request.cntr
        if not cntr:
            cntr = ([],{})
        return cntr

    def __call__(self):
        """
        Invoke the method.
        @return: The invocation result.
        @rtype: L{Return}
        """
        args, keywords = \
            (self.request.args,
             self.request.kws)
        try:
            inst, method = self.resolve()
            retval = method(*args, **keywords)
            return Return.succeed(retval)
        except Exception, e:
            log.exception(e)
            return Return.exception()

    def __str__(self):
        return str(self.request)

    def __repr__(self):
        return str(self)

#
# Security classes
#
    
class Security:
    """
    Layered Security.
    @ivar context: The auth context.
    @type context: L{RMI}.
    @ivar stack: The security stack; list of auth
        specifictions defined by decorators.
    @type stack: list
    """
    
    def __init__(self, context, fninfo):
        """
        @param context: The auth context.
        @type content: L{RMI}
        @param fninfo: The decorated function info.
        @type fninfo: L{Options}
        """
        self.context = context
        self.stack = fninfo.security

    def apply(self, passed):
        """
        Apply auth specifications.
        @param passed: The request's I{auth} info passed.
        @type passed: L{Options}.
        @raise SecretRequired: On secret required and not passed.
        @raise SecretNotMatched: On not matched.
        @raise UserRequired: On user required and not passed.
        @raise PasswordRequired: On password required and not passed.
        @raise UserNotAuthorized: On user not authorized.
        @raise NotAuthenticated: On PAM auth failed.
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
        
    def cnfn(self):
        """
        Get the I{classname} and I{function} in the context.
        @return: (classname, function-name)
        @rtype: tuple
        """
        return self.context.cnfn()

    def impl(self, name):
        """
        Find auth implementation by name.
        @param name: auth type (name)
        @type name: str
        @return: The implementation method
        @rtype: instancemethod
        """
        try:
            return getattr(self, name)
        except AttributeError:
            raise AuthMethod(self.cnfn(), name)

    def secret(self, required, passed):
        """
        Perform shared secret auth.
        @param auth: Method specific auth specification.
        @type auth: L{Options}
        @param passed: The credentials passed.
        @type passed: L{Options}
        @raise SecretRequired: On secret required and not passed.
        @raise SecretNotMatched: On not matched.
        """
        secret = required.secret
        if callable(secret):
            secret = secret()
        if not secret:
            return
        if not isinstance(secret, (list,tuple)):
            secret = (secret,)
        if not passed.secret:
            raise SecretRequired(self.cnfn())
        if passed.secret in secret:
            return
        raise SecretNotMatched(self.cnfn(), passed.secret, secret)
    
    def pam(self, required, passed):
        """
        Perform PAM authentication.
        @param required: Method specific auth specification.
        @type required: L{Options}
        @param passed: The credentials passed.
        @type passed: L{Options}
        @raise UserRequired: On user required and not passed.
        @raise PasswordRequired: On password required and not passed.
        @raise UserNotAuthorized: On user not authorized.
        @raise NotAuthenticated: On PAM auth failed.
        """
        if passed.pam:
            passed = Options(passed.pam)
        else:
            passed = Options()
        if not passed.user:
            raise UserRequired(self.cnfn())
        if not passed.password:
            raise PasswordRequired(self.cnfn())
        if passed.user != required.user:
            raise UserNotAuthorized(self.cnfn(), required.user, passed.user)
        pam = PAM()
        try:
            pam.authenticate(passed.user, passed.password, required.service)
        except Exception:
            raise NotAuthenticated(self.cnfn(), passed.user)

#
# Dispatcher classes
# 

class Dispatcher:
    """
    The remote invocation dispatcher.
    @ivar classes: The (catalog) of target classes.
    @type classes: list
    """

    def __init__(self, classes):
        """
        """
        self.classes = {}
        for c in classes:
            self.classes[c.__name__] = c
        
    def provides(self, name):
        return ( name in self.classes )

    def dispatch(self, envelope):
        """
        Dispatch the requested RMI.
        @param envelope: A request envelope.
        @type envelope: L{Envelope}
        @return: The result.
        @rtype: any
        """
        request = Request()
        request.update(envelope.request)
        request.auth = Options(
            uuid=envelope.routing[-1],
            secret=envelope.secret,
            pam=envelope.pam,)
        rmi = RMI(request, self.classes)
        log.info('dispatching:%s', rmi)
        return rmi()
