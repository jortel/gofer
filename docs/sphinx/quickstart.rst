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
   Then, set uuid=123. Or, look in ``/var/log/gofer/agent.log`` to find the auto-assigned UUID
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

