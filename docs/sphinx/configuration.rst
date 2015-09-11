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

[management]
------------

Defines agent management properties.

- **enabled** - Management is (1=enabled|0=disabled).
- **host** - The host (interface) the manager listens on.  Defaults to: `localhost`.
- **port** - The port the manager listens on.  Defaults to: `5650`.


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
- rmi

Examples:

::

 [logging]
 agent = DEBUG
 messaging = WARNING


[pam]
-----

- **service** - The (optional) service to be used for PAM authentication.


Plugin Descriptors
^^^^^^^^^^^^^^^^^^

Each plugin has a configuration located in ``/etc/gofer/plugins``.  Plugin descriptors
are *ini* style configuration files that require the following sections and properties:

[main]
------

Defines basic plugin properties.

- **name** - The (optional) plugin name.  The basename of the descriptor is used when not specified.
- **plugin** - The (optional) fully qualified path to the module to be loaded from the PYTHON path.
  When *plugin* is not specified, the plugin is loaded by searching the following directories for a
  module with the same name as the plugin:

    - /usr/share/gofer/plugins
    - /usr/lib/gofer/plugins
    - /usr/lib64/gofer/plugins
    - /opt/gofer/plugins

- **enabled** - The plugin is (1=enabled|=0disabled).
- **threads** - The (optional) number of threads for the RMI dispatcher.
- **accept** - Accept forwarding list.  Comma ',' separated list of plugin names.
- **forward** - Forwarding list.  Comma ',' separated list of plugin names.

[messaging]
-----------

- **authenticator** - The (optional) fully qualified path to a message *Authenticator* to be
  loaded from the PYTHON path.
- **uuid** - The agent identity. This value also specifies the queue name.
- **'url** - The (optional) broker connection URL.
  No value indicates the plugin should **not** connect to broker.
  *format*: ``<adapter>+<protocol>://<user>:<password>@<host>:<port>/<virtual-host>``,
  protocol is one of:

   - **tcp**:   non-SSL protocol
   - **amqp**:  non-SSL protocol
   - **ssl**:   SSL protocol
   - **amqps**: SSL protocol

  The <adapter>, <user>:<password> and /<virtual-host> are optional.
  See: :doc:`adapter` for list of supported adapters.

  The <port> is optional and defaults based on the protocol when not specified:

   - (amqp|tcp)  port:5672
   - (amqps|ssl) port:5671

- **cacert** - The (optional) SSL CA certificate used to validate the server certificate.

- **clientkey** - The (optional) SSL client private key.

- **clientcert** - The (optional) SSL client certificate.
  A (PEM) file may contain **both** the private key and certificate.

- **host_validation** - The (optional) flag indicates SSL host validation should be performed.
  Default to (1) when not specified.

- **heartbeat** - The (optional) AMQP heartbeat in seconds.  (default:10).

File extensions just be (.conf|.json).

[pending]

- **depth** - The pending queue depth.  Default: 100K


[model]
-------

- **managed** - The model is manged.  Default:2

   - 0: Not managed.
   - 1: The queue is declared on *attach* and bound the the exchange as needed.
   - 2: The queue is declared on *attach* and bound the the exchange as needed and
     drained and deleted on explicit *detach*.

- **queue** - The (optional) AMQP queue name.  This has precedent over uuid.
  Format: <exchange>/<queue> where *exchange* is optional.

- **expiration** - The (optional) auto-deleted queue expiration (seconds).

Examples
^^^^^^^^

This example enables messaging and defines the uuid:

::

 [main]
 enabled = 1

 [messaging]
 url=qpid+amqp://localhost

 [model]
 queue=123


This example enables messaging and does **not** define the uuid.  It is expected
that the plugin defines an @load decorated method/function that provides the
url and queue:

::

 [main]
 enabled = 1
 accept=*


This example does **not** enable messaging for this plugin.  This would be done when the
plugin does not need to specify an additional identity.  This example also specifies a user defined
sections to be used by the plugin:

::

 [main]
 enabled = 1

 [messaging]
 url=qpid+amqp://localhost

 [model]
 queue=123

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

