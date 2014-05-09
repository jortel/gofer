Python Examples
===============

Server-side
^^^^^^^^^^^
 
Sample server-side code:

::

 from gofer.proxy import Agent

 agent = Agent('jortel')


Sample server-side code using the proxy module API:

::

 from gofer import proxy

 agent = proxy.agent('jortel')


Define Agent-side
^^^^^^^^^^^^^^^^^

Sample agent-side code.  This module is placed in ``/var/lib/gofer/plugins/`` along with a plugin
descriptor in ``/etc/gofer/plugins/``

Plugin descriptor: ``/etc/gofer/plugins/plugin.conf``

::

 [main]
 enabled=1

 [messaging]
 url=
 uuid=jortel


Code:   ``/var/lib/gofer/plugins/plugin.py``

::

 from gofer.decorators import *
 from gofer.agent.plugin import Plugin

 # (optional) access to the plugin descriptor
 # which you can use to define custom sections/properties

 plugin = Plugin.find(__name__)
 cfg = plugin.cfg()

 class Dog:
    @remote
    def bark(self, words):
        woof = cfg.dog.bark_noise
        print '%s %s' % (woof, words)
        return 'Yes master.  I will bark because that is what dogs do.'

    @remote
    def wag(self, n):
        for i in range(0, n):
            print 'wag'
        return 'Yes master.  I will wag my tail because that is what dogs do.'


The plugin may be loaded from the PYTHON path by specifying the *plugin* property in
descriptor as follows:

::

 [main]
 enabled=1
 plugin=application.agent.plugin.py

 [messaging]
 url=
 uuid=zoo


Synchronous Invocation
^^^^^^^^^^^^^^^^^^^^^^

Sample of server code invoking synchronously methods (remotely) on the agent.  This is the default
behaviour and the timeout is 90 seconds by default.

::

 from gofer.proxy import Agent

 agent = Agent('jortel')

 # invoke methods on the agent (remotely)
 dog = agent.Dog()
 print dog.bark('hello')
 print dog.wag(3)
 print dog.bark('hello')

 # methods that raise exceptions
 try:
    print dog.sit()
 except Exception, e:
    print repr(e)

 try:
    print dog.notpermitted()
 except Exception, e:
    print repr(e)


Synchronous Invocation (specify timeout)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Sample of server code invoking synchronously methods (remotely) on the agent with a
timeout of 180 seconds.

::

 from gofer.proxy import Agent

 agent = Agent('jortel', timeout=180)  # specify timeout

 # invoke methods on the agent (remotely)
 dog = agent.Dog()
 dog.bark('hello')
 dog.wag(3)
 dog.bark('hello')


The timeout can also be a tuple: (<started>, <execute>) where the timeout specifies:

- Timeout for starting the operation
- Timeout for completing the operation.

In this example, we specify that the operation must be started by the agent within 3 seconds
and it must be completed within 180 seconds.

::

 from gofer.proxy import Agent

 agent = Agent('jortel', timeout=(3,180))  # specify timeout

 # invoke methods on the agent (remotely)
 dog = agent.Dog()
 dog.bark('hello')
 dog.wag(3)
 dog.bark('hello')



Asynchronous (fire & forget) Invocation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Sample of server code invoking synchronously methods (remotely) on the agent.  This works the same for
asynchronous *fire-and-forget* where not reply is wanted.  Asynchronous invocation returns the serial
number of the request.

::

 from gofer.proxy import Agent

 #create an agent where consumerid = "jortel"
 agent = Agent('jortel', async=True)

 # invoke methods on the agent (remotely)
 dog = agent.Dog()
 dog.bark('hello')
 dog.wag(3)
 print dog.bark('hello')
    'e688f50b-3108-43dd-9a57-813f434749a8'

 # methods that raise exceptions
 try:
    print dog.sit()
 except Exception, e:
    print repr(e)

 try:
    print dog.notpermitted()
 except Exception, e:
    print repr(e)


Asynchronous (callback) Invocation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Sample of server code invoking asynchronously methods (remotely) on the agent.   The is the *callback*
form of asynchronous invocation.  This example uses a *Listener* class.   But, the *listener* can also
be any *callable*.  Asynchronous invocation returns the serial number of the request to be used by
the caller to further correlate request & response.

::

 from gofer.proxy import Agent
 from gofer.messaging.async import ReplyConsumer

 # specify a correlation tag to be used to correlate the responses.

 ctag = 'tasks'

 # create my listener class

 class Listener:
    """
    Succeeded notification.
    reply:
        sn - request serial number.
        origin - the reply sender.
        retval - request returned value.
        any - user defined data (round tripped)
    """
    def succeeded(self, reply):
        pass

    def failed(self, reply):
        """
        Failed (exception raised) notification.
        reply:
            sn - request serial number.
            origin - the reply sender.
            exval - the raised exception.
            any - user defined data (round tripped)
        """
        pass

    def status(self, reply):
        """
        Request status changed notification.
        reply:
            sn - request serial number.
            origin - the reply sender.
            status - the new request status.
            any - user defined data (round tripped)
        """
        pass

 # create my reply consumer using the correlation tag and
 # my listener

 reader = ReplyConsumer(tag)
 reader.start(Listener())

 #create an agent where consumer ID = "jortel" and
 # setup for asynchronous invocation with my correlation tag.   The async=True
 # not needed because a ctag was specified.

 agent = Agent('jortel', ctag=tag)

 # invoke methods on the agent (remotely)
 dog = agent.Dog()
 dog.bark('hello')
 dog.wag(3)
 print dog.bark('hello')
    'e688f50b-3108-43dd-9a57-813f434749a8'


Same asynchronous example except specify a *callable* as the listener.  Also, it uses the *throw()*
method on reply.

::

 # specify a correlation tag to be used to correlate the responses.

 ctag = 'tasks'

 # create my listener

 def callback(reply):
    try:
        reply.throw()
        ...
        print reply.retval # succeeded, do something with return value.
        ...
    except WindowMissed, ex:
        # handle maintenance window missed.
        pass
    except Exception, ex:
        # handle general exception
        pass

 # create my reply consumer using the correlation tag and
 # my callback

 reader = ReplyConsumer(ctag)
 reader.start(callback)
 ...



Asynchronous (group) Invocation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Invoking operations on multiple agents is asynchronous by nature.  This can be done by simply creating
an agent (proxy) with a collection (list|tuple) of ids instead of just one.  Basically, it's the same
as the asynchronous examples above except that when more then (1) id is specified, method invocations
return a list of tuples (id, serial number) instead of just the serial number.

Eg:

::

 from gofer.proxy import Agent

 #create an agent with a list of consumer ids.
 group = ('a', 'b', 'c',)
 agent = Agent(group, ctag='tasks')
 dog = agent.Dog()
 print dog.wag(10) # request sent to (a,b,c) and asynchronous replies sent to 'tasks' queue.
   [('a', 'e688f50b-3108-43dd-9a57-813f434749a8'), ('b', 'e4e60889-edac-42f1-8b64-443dbe693566'), ('c', '95960889-edac-42f1-8b64-443dbe693f23')]


Maintenance Windows
^^^^^^^^^^^^^^^^^^^

Asynchronous invocation can define a *window* in which the agent must perform the operation.
This is intended to support *maintenance windows* but can be used for:

#. Asynchronous w/ timeout
#. Asynchronous to be performed in the future
#. 1 & 2.

In cases where the agent cannot perform the operation within the specified *window*, a *WindowMissed*
exception is raised.  In this example, we tell agents (a,b,c) dogs to wag their tails 10 times on
July 26th between 10am & 11am.

Eg:

::

 from datetime import datetime
 from gofer.proxy import Agent
 from gofer.messaging.window import Window

 #create an agent with a list of consumer ids.
 # window is on July 26th between 10am - 11am.
 group = ('a', 'b', 'c',)
 start = datetime(2010, 7, 26, 10)
 maint = Window(begin=start, hours=1)
 agent = Agent(group, ctag='tasks', window=maint)
 dog = agent.Dog()
 print dog.wag(10) # request sent to (a,b,c) and asynchronous replies sent to 'tasks' queue.
   [('a', 'e688f50b-3108-43dd-9a57-813f434749a8'), ('b', 'e4e60889-edac-42f1-8b64-443dbe693566'), ('c', '95960889-edac-42f1-8b64-443dbe693f23')]


Class Constructor Arguments
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Classes defined in the agent can have constructor arguments.  Though, remember, an instance is constructed
for each request so remote objects are stateless.  The *stub* provides for passing __init__() arguments by
calling the *stub*.

Examples:

In the plugin:

::

 class Dog:

  def __init__(self, name, age=1):
    self.name = name
    self.age = age

  @remote
  def bark(self):
    pass

  @remote
  def wag():
    pass


Calling:

::

 ...
 dog = agent.Dog()      # stub constructor, pass gofer options here.
 dog('rover', age=10)   # constructor arguments set here.
 dog.bark('hello')
 dog.wag()

 # change the constructor arguments and call something else.

 dog('max', age=5)   # changing constructor arguments.
 dog.bark('howdy')


Subsequent calls simply update the constructor arguments.

This:

::

 dog('rover', age=10)


equals this (in the agent):

::

 dog = Dog('rover', age=10)


Security
^^^^^^^^

When *remote* methods or functions are decorated to require a shared secret for request authentication,
it must be passed as an option.

Example:

::

 from gofer.proxy import Agent
 from gofer.messaging.dispatcher import NotAuthorized

 agent = Agent('jortel', secret='mycathas9lives')
 # invoke methods on the agent (remotely)
 dog = agent.Dog()
 try:
    dog.bark('secure hello')
 except NotAuthorized:
    log.error('wrong secret')


Or,

::

 from gofer.proxy import Agent
 from gofer.messaging.dispatcher import NotAuthorized

 agent = Agent('jortel')
 # invoke methods on the agent (remotely)
 dog = agent.Dog(secret='mycathas9lives')
 try:
    dog.bark('secure hello')
 except NotAuthorized:
    log.error('wrong secret')


Progress Reporting
^^^^^^^^^^^^^^^^^^

In gofer 0.72+ remote method progress can be reported by plugins.  In the case of synchronous RMI, the caller
can specify a *callback* for progress reporting by specifying the *progress* option.  The *callback* must
take a single (dict) parameter (report).

The report has the following keys:

- **sn** - *serial number*
- **any** - *user data*
- **total** - *the number total units*
- **completed** - *the number of completed units*
- **details** - *arbitrary details*

For asynchronous RMI, the *listener* is called with progress reports.

Examples:

::

 from gofer.proxy import Agent

 def progress_reported(report)
  pass

 agent = Agent()
 dog = agent.Dog(progress=progress_reported)
 dog.bark('howdy')


On the agent, plugins report progress from with a method by using the *Progress* object defined within
the current call *Context*.

Example:

::

 from gofer.agent.rmi import Context
 from gofer.decorators import remote

 class MyClass:

    @remote
    def foo(self):
        """
        Do something reports progress
        """
        total = 10
        # get the call context
        ctx = Context.current()
        ctx.progress.total = total
        # demo reporting progress for 10 units
        for n in range(0, total):
            ctx.progress.completed += 1
            sleep(1)

    @remote
    def bar(self):
        """
        Do something reports progress with details.
        """
        total = 10
        # get the call context
        ctx = Context.current()
        ctx.progress.total = total
        # demo reporting progress for 10 units
        for n in range(0, total):
            ctx.progress.completed += 1
            ctx.progress.details='for: %d' % n)
            sleep(1)


Testing
^^^^^^^

Logs
----

After adding/updating classes or methods in myplugin.py, you'll want to test them.  First, ensure the
plugin is still loading properly.  The easiest way to do this is by examining the gofer log file
at: ``/var/log/gofer/agent``.  At start up, you should see something like:

::

 2010-11-08 08:49:04,491 [WARNING][MainThread] __mangled() @ plugin.py:122 - "pulp" found in python-path
 2010-11-08 08:49:04,503 [INFO][MainThread] __mangled() @ plugin.py:123 - "pulp" mangled to avoid collisions
 2010-11-08 08:49:04,909 [INFO][MainThread] __import() @ plugin.py:103 - plugin "pulp", imported as: "pulp_plugin"


Either the gofer log or the pulp client.log may be examined to verify that *Actions* are
running as expected.

Interactive Shell
-----------------

Testing added/updated *remote methods*, can be done easily using an interactive python (shell).
Be sure your changes to the pulp plugin have been picked up by *Gofer* by **restarting goferd**.
Let's say you added a new class named "Foo" that has a remote method named ... you guessed it: "bar".

You can test your new stuff as follows:

::

 [jortel@localhost pulp]$ python
 Python 2.6.2 (r262:71600, Jun  4 2010, 18:28:04)
 [GCC 4.4.3 20100127 (Red Hat 4.4.3-4)] on linux2
 Type "help", "copyright", "credits" or "license" for more information.
 >>> from gofer.proxy import Agent
 >>> uuid = <your consumer ID>
 >>> agent = Agent(uuid)
 >>> foo = agent.Foo()
 >>> print foo.bar()


Or, using the proxy module API:

::

 [jortel@localhost pulp]$ python
 Python 2.6.2 (r262:71600, Jun  4 2010, 18:28:04)
 [GCC 4.4.3 20100127 (Red Hat 4.4.3-4)] on linux2
 Type "help", "copyright", "credits" or "license" for more information.
 >>> from gofer import proxy
 >>> uuid = <your consumer ID>
 >>> agent = proxy.agent(uuid)
 >>> foo = agent.Foo()
 >>> print foo.bar()

Admin.help()
------------

Another useful tool, it invoke *Admin.help()* from within interactive python as follows:

::

 [jortel@localhost pulp]$ python
 Python 2.6.2 (r262:71600, Jun  4 2010, 18:28:04)
 [GCC 4.4.3 20100127 (Red Hat 4.4.3-4)] on linux2
 Type "help", "copyright", "credits" or "license" for more information.
 >>> from pulp.server.agent import Agent
 >>> uuid = <your consumer ID>
 >>> agent = Agent(uuid)
 >>> admin = agent.Admin()
 >>> print admin.help()

 Plugins:
   builtin
   pulp [pulp_admin]
 Actions:
   builtin.TestAction 0:10:00
 Methods:
   custom.Dog.bark()
   custom.Dog.wag()
   builtin.Admin.hello()
   builtin.Admin.help()
   builtin.Shell.run()
 Functions:
   builtin.echo()
 >>>


Test Main
---------

The ``test/main.py`` module provides a good testing entry point that does not require the process owner
to be root.

Mocks
-----

The gofer *mock* feature provides better testability.  Essentially, it allows uses to test the
server-side code that uses the gofer proxy.  Instead of calling through to the remote agent,
RMI calls can be mocked-up.

Added 0.33.

The *mock* module provides an API for registering custom *stub* mocks.

Items that can be registered with *mock*.register():

- instance (object)
- class
- module

Example:

::

 from gofer.messaging import mock
 mock.install()
 from gofer.proxy import Agent

 agent = Agent('xyz')

 # define mock impl for testing
 class Dog:
    def bark(self, msg):
        return 'mock Dog, called with: [%s]' % msg

 # register our mock class
 mock.register(Dog=Dog)

 # call bark()

 dog = agent.Dog()

 print dog.bark('hello')
   'mock Dog, called with: [hello]'

 print dog.bark('world')
   'mock Dog, called with: [world]'

 #
 # now, let look at the call history
 #

 h =  dog.bark.history()
 print h
  '[("hello",),{}), ("world",),{})]'

 # get last call
 last = h[-1]

 # look at the passed args
 print last.args[0]
  'world'

 # look at the keyword args
 print last.kwargs
  '{}'


It's very important to note the difference between registering a class (as a stub) and an instance
(as a stub).  In short, nstances are shared across all *mock* agents and classes are associated to
the instance of the *mock* agent that created them.  That way, call history is scoped to *mock*
agent as well.

In some cases, it's useful to have a stub method raise an exception.  Here's how it's done:

::

 from gofer.messaging import mock
 mock.install()
 from gofer.proxy import Agent

 agent = Agent('xyz')

 # define mock impl for testing
 class Dog:

    def bark(self, msg):
        return 'mock Dog, called with: [%s]' % msg

 # register our mock class
 mock.register(Dog=Dog)

 dog = agent.Dog()

 # call bark() normally
 print dog.bark('hello')

 # now, let's have it raise an exception

 dog.bark.push(Exception('no more barking'))
 try:
    dog.bark('hello')
 except Exception, e:
   print e
   '"no more barking'"

