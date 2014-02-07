Configuration
=============

The gofer agent and plugins are configured using *ini* style configuration
files located in ``/etc/gofer``.

Agent Configuration
^^^^^^^^^^^^^^^^^^^

The agent configuration is specified in: ``/etc/gofer/agent.conf`` and through
files located in ``/etc/gofer/conf.d``.  During startup, gofer first reads
``agent.conf``.  Then, reads and merges in values found in the ``conf.d`` files.

All configuration files support the following sections and properties:

[logging]
---------

This section sets logging properties.  Currently, the logging level can be set for each
gofer packege as follows:

::

 <package> = <level>


Levels (may be lower case):

- CRITICAL
- DEBUG
- ERROR
- FATAL
- INFO
- WARN
- WARNING

Gofer packages:

- agent
- messaging
- plugins

Examples:

::

 [logging]
 agent = DEBUG
 messaging = WARNING


[messaging]
-----------

Defines messaging properties:

- **url** - The broker connection URL.
  No value indicates that gofer should **not** connect to the broker.
    *format*: *<protocol>://<host>:<port>*, protocol is one of:
      - **tcp**: non-SSL protocol
      - **amqp**: non-SSL protocol
      - **ssl**: SSL protocol
      - **amqps**: SSL protocol
- **transport** - The transport used to connect to the specified broker.
- **cacert** - The (optional) SSL CA certificate used to validate the server certificate.
- **clientcert** - The (optional) SSL client certificate.
  A (PEM) file containing **both** the private key and certificate.
- **threads** - The (optional) number of threads for the RMI dispatcher.
  Default to (1) when not specified.

Example:

::

 [messaging]
 url = tcp://localhost:5672
 transport: amqplib
 cacert = /etc/pki/qpid/ca/ca.crt
 clientcert = /etc/pki/qpid/client/client.pem


[loader]
--------

Defines plugin loading properties.

.. _note: added 0.51.

- **eager** - Eager loading of plugins (default: 1)
   - 0 - disabled plugins not loaded
   - 1 - disabled plugins loaded but not started or exposed


Plugin Descriptors
^^^^^^^^^^^^^^^^^^

Each plugin has a configuration located in ``/etc/gofer/plugins``.  Plugin descriptors
are *ini* style configuration that require the following sections and properties:

[main]
------

Defines basic plugin properties.

- **enabled** - Specify the plugin as enabled/disabled.
- **requires** -  Specify (optional) required (,) comma separated list of plugins by name.
  Ensure proper loading order.

[messaging]
-----------

- **enabled** - Specify the plugin as enabled/disabled.
- **uuid** - The default agent (UUID) identity.
  This value may be overridden by an *identity* plugin.
- **'url** - The (optional) QPID connection URL.
  No value indicates the plugin should **not** connect to broker.
    format:  *<protocol>://<host>:<port>*, protocol is one of:
      - **tcp**: non-SSL protocol
      - **amqp**: non-SSL protocol
      - **ssl**: SSL protocol
      - **amqps**: SSL protocol
- **transport** - The transport used to connect to the specified broker.
- **cacert** - The (optional) SSL CA certificate used to validate the server certificate.
- **clientcert** - The (optional) SSL client certificate.  A (PEM) file containing **both**
  the private key and certificate.
- **validation** - Enable SSL host validation.
- **threads** - The (optional) number of threads for the RMI dispatcher.
  Default to (1) when not specified.

This example enables messaging and defines the uuid:

::

 [main]
 enabled = 1

 [messaging]
 enabled = 1
 uuid=123


This example enables messaging and does **not** define the uuid.  It is expected
that the plugin defines an @identity decorated method/function that provides the
uuid:

::

 [main]
 enabled = 1

 [messaging]
 enabled = 1


This example does **not** enable messaging for this plugin.  This would be done when the
plugin does not need to specify an additional identity.  This example also specifies a user defined
sections to be used by the plugin:

::

 [main]
 enabled = 1

 [messaging]
 enabled = 0

 [foobar]
 timeout = 100


However, additional user defined sections and properties are supported and made available to
the plugin(s) as follows:

::


  from gofer.agent.plugin import Plugin
  ...
  class MyPlugin:
    ...
    def mymethod(self):
        cfg = Plugin.find(__name__).cfg()
        timeout = cfg.foobar.timeout
        ...

Directives & Macros
^^^^^^^^^^^^^^^^^^^

The /etc/gofer/agent.conf, conf.d/*.conf files and plugin descriptors support predefined directives and
macros.  They are provided as a convenience because gofer is designed to use in conjunction with other
applications.

Directives
----------

The following are supported directives.

@import
+++++++

The *@import* directive is used to import all or portions of another INI file into gofer
configurations and plugin descriptors.  It has the following form:

::

 @import : <path> : <section> : <property> ,

Where:

 **path**
    The absolute path to an INI file.

 **section**
    The (optional) section to import.  ALL sections when not specified.

 **property**
    The (optional) (,) separated list of property specifications.  ALL properties when not specified.

The *property* specification tasks (2) forms:

 **name**
    Import the property.  Acts like filter.

 **name** ( *variable* )
    Import the property value but assign to *variable* instead of actually importing.

Variables are referenced as: $(*variable*)

Eg:

::

 My $(name) is Earl.


Examples:

/etc/foo.conf

::

 [server]
 host=foo.com
 port=9000

 [threads]
 min=1
 max=100


My configuration: bar.conf

::

 @import:/etc/foo.conf
 [bar]
 name=Elmer Fudd
 age=33


Results in:

::

 [bar]
 name=Elmer Fudd
 age=33

 [server]
 host=foo.com
 port=9000

 [threads]
 min=1
 max=100


Or, only import the *threads* section:

My configuration: bar.conf

::

 @import:/etc/foo.conf:threads
 [bar]
 name=Elmer Fudd
 age=33

Results in:

::

 [bar]
 name=Elmer Fudd
 age=33

 [threads]
 min=1
 max=100

Now, let's only import the *server* *host*:

My configuration: bar.conf

::

 @import:/etc/foo.conf:server:host
 [bar]
 name=Elmer Fudd
 age=33

Results in:

::

 [bar]
 name=Elmer Fudd
 age=33

 [server]
 host=foo.com

Now, let's only import the *server* *port* and defined the *host* as a variable named *foohost* and use it:

My configuration: bar.conf

::

 @import:/etc/foo.conf:server:host(foohost),port
 [bar]
 host=$(foohost)
 name=Elmer Fudd
 age=33

Results in:

::

 [bar]
 host=foo.com
 name=Elmer Fudd
 age=33

 [server]
 port=foo.com


Macros
------

Macros are built-in functions that can be used in any part of configuration files.

Built-in macros:

%{hostname}
+++++++++++

The **%{hostname}** evaluates to the current *hostname*.

Eg:

My configuration:

::

 [server]
 host=%{hostname}
 port=123

Evaluates to:

::

 [server]
 host=abc.redhat.com
 port=123

Like variables, macros may be embedded in other text:

::

 [server]
 host=xyz.%{hostname}
 port=123

Evaluates to:

::

 [server]
 host=xyz.abc.redhat.com
 port=123

