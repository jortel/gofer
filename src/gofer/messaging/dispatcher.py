#
# Copyright (c) 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
#
"""
Provides RMI dispatcher classes.
"""

import sys
import inspect
import traceback as tb
from threading import Thread
from gofer.messaging import *
from gofer.messaging.threadpool import ThreadPool
from logging import getLogger


log = getLogger(__name__)


class DispatchError(Exception):
    pass


class ClassNotFound(DispatchError):
    """
    Target class not found.
    """

    def __init__(self, classname):
        Exception.__init__(self, classname)


class MethodNotFound(DispatchError):
    """
    Target method not found.
    """

    def __init__(self, classname, method):
        message = '%s.%s(), not found' % (classname, method)
        Exception.__init__(self, message)


class NotPermitted(DispatchError):
    """
    Called method not decorated as I{remote}.
    """

    def __init__(self, cnfn):
        message = '%s.%s(), not permitted' % cnfn
        Exception.__init__(self, message)
        
        
class NotShared(DispatchError):
    """
    Method not shared between UUIDs.
    """

    def __init__(self, cnfn):
        message = '%s.%s(), not shared' % cnfn
        Exception.__init__(self, message)


class NotAuthorized(DispatchError):
    """
    Not authorized, secret not matched.
    """

    def __init__(self, cnfn):
        message = '%s.%s(), not authorized' % cnfn
        Exception.__init__(self, message)
        
        
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
                mod = __import__(mod, fromlist=[classname,])
                C = getattr(mod, classname)
            inst = cls.__new(C)
            inst.__dict__.update(state)
            if isinstance(inst, Exception):
                inst.args = args
            return inst
        except Exception,e:
            pass
        return RemoteException(reply.exval)
    
    @classmethod
    def __new(cls, C):
        try:
            import new
            return new.instance(C)
        except:
            pass
        return Exception.__new__(C)


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
        return Return(retval=x)

    @classmethod
    def exception(cls):
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
        state = inst.__dict__
        return Return(exval=exval,
                      xmodule=mod,
                      xclass=xclass.__name__,
                      xstate=state,
                      xargs=args)

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
            return inst()
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
        cn, fn = self.__cnfn()
        if hasattr(inst, fn):
            method = getattr(inst, fn)
            return self.permitted(method)
        else:
            raise MethodNotFound(cn, fn)
        
    def permitted(self, method):
        """
        Check whether remote invocation of the specified method is permitted.
        @param method: The method in question.
        @type method: (method|function)
        @return: True if permitted.
        @rtype: bool
        """
        auth = self.request.auth
        fninfo = self.__fninfo(method)
        if fninfo is None:
            raise NotPermitted(self.__cnfn())
        self.__shared(fninfo, auth)
        self.__authorized(fninfo, auth)
        return method
        
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
        raise NotShared(self.__cnfn())
        
    def __authorized(self, fninfo, auth):
        """
        Validate the method was decorated by specifying
        a I{secret} and that if matches the I{secret}
        passed with the request.  The secret may be I{callable} in
        which case it is invoked and the returned value is tested against
        the secret passed in the request.
        @param fninfo: The decorated function info.
        @type fninfo: L{Options}
        @param auth: The request's I{auth} info.
        @type auth: L{Options}
        @raise NotAuthorized: On secret specified and not matched.
        """
        secret = fninfo.secret
        if not secret:
            return
        if callable(secret):
            secret = secret()
        if not secret:
            return
        if not isinstance(secret, (list,tuple)):
            secret = (secret,)
        log.debug('match secret: "%s" in "%s"', auth.secret, secret)
        if auth.secret in secret:
            return
        raise NotAuthorized(self.__cnfn())
    
    def __cnfn(self):
        """
        Get the I{classname} and I{function} specified in the request.
        @return: (classname, function-name)
        @rtype: tuple
        """
        return (self.request.classname,
             self.request.method)

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
            return self.__fn(method).gofer
        except:
            pass

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


class Dispatcher:
    """
    The remote invocation dispatcher.
    @ivar classes: The (catalog) of target classes.
    @type classes: list
    """

    def __init__(self):
        """
        """
        self.classes = {}

    def register(self, *classes):
        """
        Register classes exposed as RMI targets.
        @param classes: A list of classes
        @type classes: [cls,..]
        @return self
        @rtype: L{Dispatcher}
        """
        for cls in classes:
            self.classes[cls.__name__] = cls
        return self
    
    def concurrent(self):
        """
        Get whether the dispatcher is concurrent.
        @return: False
        @rtype: bool
        """
        return False

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
            uuid=envelope.destination.uuid,
            secret=envelope.secret,)
        rmi = RMI(request, self.classes)
        log.info('dispatching:%s', rmi)
        return rmi()


class ReplyThread(Thread):
    """
    Dispatcher reply (worker) thread.
    @ivar __run: The main run/read flag.
    @type __run: bool
    @ivar dispatcher: A dispatcher that is notified when
        replies are received.
    @type dispatcher: L{Dispatcher}
    """

    def __init__(self, dispatcher):
        """
        @param dispatcher: A dispatcher that is notified when
            replies are read.
        @type dispatcher: L{Dispatcher}
        """
        Thread.__init__(self, name='ReplyThread')
        self.__run = True
        self.dispatcher = dispatcher
        self.setDaemon(True)

    def run(self):
        """
        Replies are read from dispatcher.pool and
        dispatched to the dispatcher.replied().
        """
        reply = None
        while self.__run:
            try:
                reply = self.pool.get()
                if reply:
                    self.dispatcher.replied(reply)
                log.debug('ready')
            except:
                log.error('failed:\n%s', reply, exc_info=True)

    def stop(self):
        """
        Stop reading and terminate the thread.
        """
        self.__run = False
    
    @property
    def pool(self):
        return self.dispatcher.pool


class ConcurrentDispatcher(Dispatcher):
    """
    The remote invocation dispatcher.
    @ivar cb: The reply callback.
    @type cb: callable
    @ivar pool: Thread pool.
    @type pool: L{ThreadPool}
    @ivar replythread: The reply reader thread.
    @type replythread: L{ReplyThread}
    """
    
    def __init__(self, min=1, max=10):
        Dispatcher.__init__(self)
        self.cb = None
        self.pool = ThreadPool(min, max)
        self.replythread = ReplyThread(self)
        self.replythread.start()
        
    def concurrent(self):
        """
        Get whether the dispatcher is concurrent.
        @return: True
        @rtype: bool
        """
        return True

    def dispatch(self, envelope, cb):
        """
        Dispatch the requested RMI.
        @param envelope: A request envelope.
        @type envelope: L{Envelope}
        @param cb: The reply callback.
        @type cb: callable
        """
        self.cb = cb
        self.pool.run(Dispatcher.dispatch, self, envelope)
        
    def replied(self, reply):
        """
        Reply from execution in thread pool.
        @param reply: The reply (call, retval)
        @type reply: tuple
        """
        if callable(self.cb):
            call, result = reply
            envelope = call[1][1]
            self.cb(envelope, result)
        else:
            raise Exception,\
                'callback: %s, not valid' % self.cb
