Tools
=====

The gofer project includes the follow tools.

Command Line Interface
^^^^^^^^^^^^^^^^^^^^^^

The ``gofer`` CLI provides both management (MGT) of *goferd* and remote method invocation (RMI).
The management tool may be used to get the status of *goferd* and to dynamically load, reload and
unload plugins.  The management tool connects to *goferd* on the management port as defined in
``/etc/gofer/agent.conf``.  Management must be explicitly enabled.

::

 [management]
 enabled=1
 host=localhost
 port=5650

The RMI tool may be used to remotely invoke methods provided by plugins.  It does not need management
to be enabled.

.. note::
  The CLI is new in gofer 2.7

Examples
--------

The following are example of what can be done using ``gofer``.  It's assumed that management has
been enabled on the default port and the host name is ``localhost``.  When configured with these
defaults, the ``(-h|--host) and (-p|--port)`` are not necessary but shown in the examples for
for better illustration.

See: ``man gofer`` for complete details.

Show the status of goferd
+++++++++++++++++++++++++

::

 $ gofer mgt -h localhost -p 5650 -s
    Plugins:
    
      <plugin> package
        Classes:
          <class> Package
            methods:
              install(name)
              remove(name)
              update(name)
        Functions:
    
      <plugin> virt
        Classes:
          <class> Virt
            methods:
              getDomainID(name)
              isAlive(id)
              listDomains()
              shutdown(id)
              start(id)
        Functions:
    
      <plugin> __builtin__
        Classes:
          <class> Admin
            methods:
              cancel(sn, criteria)
              echo(text)
              hello()
              help()
        Functions:
    
      <plugin> system
        Classes:
          <class> Shell
            methods:
              run(cmd)
          <class> System
            methods:
              cancel()
              halt(when)
              reboot(when)
          <class> Service
            methods:
              restart()
              start()
              status()
              stop()
          <class> Script
            methods:
              run(user, password, *options)
        Functions:
    
      <plugin> builtin
        Classes:
          <class> Builtin
            methods:
              demo()
              echo(something)
              hello()
        Functions:
    
    Actions:

Load a plugin
+++++++++++++

Plugins can be dynamically loaded using the path to its descriptor.

::

 $ gofer mgt -h localhost -p 5650 -s
    Plugins:
    Actions:

 $ gofer mgt -h localhost -p 5650 -l /opt/gofer/plugins/package.conf
 $ gofer mgt -h localhost -p 5650 -s
    Plugins:

      <plugin> package
        Classes:
          <class> Package
            methods:
              install(name)
              remove(name)
              update(name)
        Functions:

    Actions:


Reload a plugin
+++++++++++++++

Plugins can be dynamically reloaded by name or path to its descriptor.

::

 $ gofer mgt -h localhost -p 5650 -r package

Unload a plugin
+++++++++++++++

Plugins can be dynamically unloaded by name or using the path to its descriptor.

::

 $ gofer mgt -h localhost -p 5650 -s
    Plugins:

      <plugin> package
        Classes:
          <class> Package
            methods:
              install(name)
              remove(name)
              update(name)
        Functions:

    Actions:

 $ gofer mgt -h localhost -p 5650 -u package
 $ gofer mgt -h localhost -p 5650 -s
    Plugins:
    Actions:


Remote Method Invocation
------------------------

The following examples assume a plugin is loaded in *goferd* at the URL of ``qpid+amqp://localhost``
and subscribed to the *demo* queue.  So ``-a demo`` will be the *address* used.  Further, it's assumed
that the plugin provides the following API.

::

 class Dog(object):

     @remote
     def bark(self, words):
         return 'Yes master.  I will bark because that is what dogs do. "%s"' % words

    @remote
    def wag(self, n):
        for i in range(0, n):
            print 'wag'
        return 'Yes master.  I will wag my tail because that is what dogs do.'

Synchronous RMI
+++++++++++++++

::

 $ gofer rmi -u qpid+amqp://localhost -a demo -t Dog.bark howdy

   Yes master.  I will bark because that is what dogs do. "howdy"

 $ gofer rmi -u qpid+amqp://localhost -a demo -t Dog.wag 3

   Yes master.  I will wag my tail because that is what dogs do.


Asynchronous RMI
++++++++++++++++

The following uses the ``-r <address`` option to specify that the reply is to
be sent to the *replies* AMQP address (queue).

::

 $ gofer rmi -u qpid+amqp://localhost -a demo -r replies -t Dog.bark howdy

   719d234f-480d-4035-9c2b-b08d17d77f13


