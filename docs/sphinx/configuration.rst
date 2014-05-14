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
  *format*: *<protocol>://<user>:<password>@<host>:<port>/<virtual-host>*, protocol is one of:

   - **tcp**:   non-SSL protocol
   - **amqp**:  non-SSL protocol
   - **ssl**:   SSL protocol
   - **amqps**: SSL protocol

  The <user>:<password> and /<virtual-host> are optional. The <port> is optional and defaults
  based on the protocol when not specified:

   - (amqp|tcp)  port:5672
   - (amqps|ssl) port:5671

- **transport** - The transport used to connect to the specified broker.
- **cacert** - The (optional) SSL CA certificate used to validate the server certificate.
- **virtual_host** - The (optional) broker virtual host.
- **clientcert** - The (optional) SSL client certificate.
- **host_validation** - The (optional) flag indicates SSL host validation should be performed.
- **userid** - The (optional) userid used for authentication.
- **password** - The (optional) password used for authentication.
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


Plugin Descriptors
^^^^^^^^^^^^^^^^^^

Each plugin has a configuration located in ``/etc/gofer/plugins``.  Plugin descriptors
are *ini* style configuration that require the following sections and properties:

[main]
------

Defines basic plugin properties.

- **name** - The (optional) plugin name.  The basename of the descriptor is used when not specified.
- **plugin** - The (optional) fully qualified module to be loaded from the PYTHON path.
  When *plugin* is not specified, the plugin is loaded by searching the following directories for a
  module with the same name as the plugin:

    - /usr/share/gofer/plugins
    - /usr/lib/gofer/plugins
    - /usr/lib64/gofer/plugins
    - /opt/gofer/plugins

- **enabled** - Specify the plugin as enabled/disabled.
- **requires** -  Specify (optional) required (,) comma separated list of plugins by name.
- **extends** - Specify (optional) another plugin to extend by name.

[messaging]
-----------

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

