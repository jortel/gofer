Getting Started
===============

Installation
^^^^^^^^^^^^

First, install and start QPID (qpidd)

Then,

1. Install gofer

   ::

     yum install gofer

2. Edit the ``/etc/gofer/plugins/builtin.conf`` and set the url to point at your broker.
   Then, set uuid=123. Or, look in ``/var/log/messages`` to find the auto-assigned UUID
   for your system.

   ::

     [main]
     enabled=1

     [messaging]
     url=tcp://localhost:5672
     uuid=123

3. Start the gefer service (goferd)

   ::

     service goferd start

4. Now, invoke the remote operations provided by the builtin plugin:

Python
------

   ::

     >>> from gofer.proxy import Agent
     >>> agent = Agent('123')
     >>> admin = agent.Admin()
     >>> print admin.help()
         Plugins:
           builtin
         Actions:
           builtin.TestAction.hello() 0:10:00
         Methods:
          Admin.hello()
          Admin.help()
          Shell.run()
        Functions:
          builtin.echo()

Ruby
----

  ::

    irb
    irb(main):001:0> require 'gofer'
    irb(main):001:0> agent = Gofer::Agent.new('123')
    irb(main):001:0> admin = agent.Admin.new()
    irb(main):001:0> puts admin.help()
        Plugins:
          builtin
        Actions:
          builtin.TestAction.hello() 0:10:00
        Methods:
         Admin.hello()
         Admin.help()
         Shell.run()
       Functions:
         builtin.echo()



Writing A Plugin
^^^^^^^^^^^^^^^^

The installing plugins is done in 6 easy steps. 

#. Write your plugin descriptor.
#. Write your plugin module.
#. Copy (or symlink) the plugin descriptor (myplugin.conf) to /etc/gofer/plugins/
#. Copy (or symlink) the plugin module (myplugin.py) to /usr/lib/gofer/plugins/
#. Restart *goferd*
#. Add server side code to invoke remote methods

Let's create a plugin named *myplugin*.  

Step 1
------

Create your plugin descriptor (myplugin.conf) as follows:

::

 [main]
 enabled = 1

 [messaging]
 uuid=123


Step 2
------

Write your plugin.  It will be defined in a module named *myplugin.py* and would look
something like this:

::

 from gofer.decorators import  *

 class MyClass:

    @remote
    def hello(self):
        return 'MyPlugin says, "hello".'


Stand alone (plain) functions may be decorated as *remote*.

Your class may have constructor arguments.

::

 from gofer.decorators import  *

 @remote
 def hello(self):
    return 'MyPlugin says, "hello".'


Step 3
------

Install or update your plugin descriptor.

::

 cp myplugin.conf /etc/gofer/plugins


Step 4
------

Install or update your plugin.

::

 cp myplugin.py /usr/lib/gofer/plugins


Step 5
------

Restart the gofer daemon.

::

 sudo /etc/sbin/service goferd restart


Step 6
------

Add *server-side* code to invoke methods on your plugin.

This is done by instantiating a *proxy* for the agent.  You need to specifying the *uuid* of the
agent (plugin).

::

 ...
 # your server code
 from gofer.proxy import Agent
 uuid = '123'
 agent = Agent(uuid)
 myclass = agent.MyClass()
 myclass.hello()


Invoke the stand alone function.  Instead of instantiating the remote class, the function
is invoked directly using the plugin module's namespace:

::

 ...
 # your server code
 from gofer.proxy import Agent
 uuid = '123'
 agent = Agent(uuid)
 agent.myplugin.hello()


Interactive Testing
^^^^^^^^^^^^^^^^^^^

After adding classes or methods in myplugin.py, you'll want to test them.  First, ensure the plugin is
still loading properly.  The easiest way to do this is by examining the gofer log file
at: /var/log/gofer/agent.  At start up, you should see something like:

::

 2010-11-08 08:49:04,909 [INFO][MainThread] __import() @ plugin.py:103 - plugin "myplugin", imported as: "myplugin"


The gofer log (/var/log/messages) may be examined to verify that *Actions* are running as expected.
Also, RMI requests (massages) are logged upon receipt in the gofer agent log.

Testing added *remote methods*, can be done easily using an interactive python (shell).  Be sure your
changes to *your* plugin have been picked up by *Gofer* by **restarting goferd**.  Let's say you added
a new class named "Foo" that has a remote method named ... you guessed it: "bar".  You can test your
new stuff as follows:

::

 [jortel@localhost pulp]$ python
 Python 2.6.2 (r262:71600, Jun  4 2010, 18:28:04)
 [GCC 4.4.3 20100127 (Red Hat 4.4.3-4)] on linux2
 Type "help", "copyright", "credits" or "license" for more information.
 >>> from gofer.proxy import Agent
 >>> uuid = '123'
 >>> agent = Agent(uuid)
 >>> myclass = agent.MyClass()
 >>> print myclass.hello()
 MyPlugin says, "hello".


Another useful tool, it invoke *Admin.help()* from within interactive python as follows:

::

 [jortel@localhost pulp]$ python
 Python 2.6.2 (r262:71600, Jun  4 2010, 18:28:04)
 [GCC 4.4.3 20100127 (Red Hat 4.4.3-4)] on linux2
 Type "help", "copyright", "credits" or "license" for more information.
 >>> from gofer.proxy import Agent
 >>> uuid = '124'
 >>> agent = Agent(uuid)
 >>> admin = agent.Admin()
 >>> print admin.help()

 Plugins:
   builtin
   myplugin
 Actions:
   builtin.TestAction 0:10:00
 Methods:
   myplugin.MyClass.hello()
   builtin.AgentAdmin.hello()
   builtin.AgentAdmin.help()
   builtin.Shell.run()
 Functions:
   builtin.echo()
 >>>


Security
--------

The @remote decorator and gofer infrastructure supports (1) option:

- secret (default=None): A shared secret used for authentication.  The value may be:

  - str
  - [str,..]
  - (str,..)
  -  *callable*


In this example, MyClass.hello() must provide the *secret* to be invoked.

::

 c = agent.MyClass(secret='mycathas9lives')
 c.hello()


::

 from gofer.decorators import  *

 class MyClass:

    @remote(secret='mycathas9lives')
    def hello(self):
        return 'MyPlugin says, "hello".'

The decorator also support the *secret* being a callable that returns the secret matched to the request.

Example:

::

 from gofer.decorators import  *

 def getsecret():
    ...
   return secret

 class MyClass:

    @remote(secret=getsecret)
    def hello(self):
        return 'MyPlugin says, "hello".'

