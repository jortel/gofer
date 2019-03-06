Getting Started
===============

Installation
^^^^^^^^^^^^

First, install and start QPID (qpidd)

Then,

1. Install gofer.

   ::

     yum install gofer python-gofer-qpid

2. Edit the ``/etc/gofer/plugins/demo.conf`` and set the url to point at your broker.
   Then, set queue=123. Or, look in ``/var/log/messages`` to find the auto-assigned *address*
   for your system.

   ::

   [main]
   enabled = 1

   [messaging]
   url=qpid+amqp://localhost

   [model]
   queue=123

3. Start the goferd service.

   ::

     service goferd start

4. Now, invoke the remote operations provided by the demo plugin:

Python
------

   ::

     >>> from gofer.proxy import Agent
     >>>
     >>> url = 'amqp://localhost'
     >>> agent = Agent(url, '123')
     >>> admin = agent.Admin()
     >>> print admin.help()
         Plugins:
           demo
         Actions:
           demo.TestAction.hello() 0:10:00
         Methods:
          Admin.hello()
          Admin.help()
          Shell.run()
        Functions:
          demo.echo()


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
 url=qpid+amqp://localhost

 [model]
 queue=123


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

This is done by instantiating a *proxy* for the agent.  You need to specifying the *address* of the
agent (plugin).

::

 ...
 # your server code
 from gofer.proxy import Agent

 url = 'amqp://localhost'
 address = '123'
 agent = Agent(url, address)
 myclass = agent.MyClass()
 myclass.hello()


Invoke the stand alone function.  Instead of instantiating the remote class, the function
is invoked directly using the plugin module's namespace:

::

 ...
 # your server code
 from gofer.proxy import Agent

 url = 'amqp://localhost'
 address = '123'
 agent = Agent(url, address)
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
 >>>
 >>> url = 'amqp://localhost'
 >>> address = '123'
 >>> agent = Agent(url, address)
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
 >>>
 >>> url = 'amqp://localhost'
 >>> address = '123'
 >>> agent = Agent(url, address)
 >>> admin = agent.Admin()
 >>> print admin.help()

 Plugins:
   demo
   myplugin
 Actions:
   demo.TestAction 0:10:00
 Methods:
   myplugin.MyClass.hello()
   demo.AgentAdmin.hello()
   demo.AgentAdmin.help()
   demo.Shell.run()
 Functions:
   demo.echo()
 >>>
