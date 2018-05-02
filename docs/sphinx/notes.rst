Release Notes
=============

gofer 1.4
^^^^^^^^^

Here is a summary of 1.0 changes:

- Support for multiple *transports* was added.
- Message authentication added.
- The *accepted* status reply was added.
- The *watchdog* as removed.
- An ISO 8601 timestamp is included in all reply messages.

gofer 2.0
^^^^^^^^^

The 2.0 major release and contains API changes, minor message format changes
and the removal of deprecated functionality. The goal of this release was to overhaul
and streamline may major component and flows. This release also contains hundreds of new unit
integration and unit tests as part of a major effort to reach 100% test coverage.


Overhauled:

- The agent thread pool was replaced with *Queue* based approach.
- Support for multiple messaging libraries. Standard messaging adapter model that
  uses delegation pattern instead of python meta-classes. Much better.


Concept changes
---------------

- The *transport* concept was replaced with *messaging adapters*. Each *adapter* implements
  an interface defined in the adapter model and provides integration with 3rd part AMQP
  messaging libraries. The *transport* option and descriptor property replaced with
  rich protocol handler support in the URL. See documented URL.

- All options are only supported when creating the agent proxy. They are no longer supported
  when constructing the stub. This semantic is not reserved for passing arguments to the remote
  object (class) constructor.

- The agent *uuid* is being phased out. RMI calls are routed to the agent based on the
  queue on which it was received. This term is being replaced by more AMQP related
  terms and concepts. An address has the format of: *exchange*/*queue* or *queue*.

- Support for agent broadcast was removed. This feature was deemed as not useful since
  most applications do not track requests using the serial number. Also, this can be
  easily implemented by the caller. Removed to make code paths and the API simpler.

API changes
-----------

There are API changes that affect both RMI calling (proxy) and the Plugin object exposed
to agent plugins. Proxy changes pertain to the options passed to the *Agent* class and the
*Stubs* created.

The *Agent* constructor changed from: Agent(uuid, **options) to: Agent(url, address, **options).

Example (adapter = qpid)::

 url = qpid+amqp://localhost


Option changes:

- *async* - Removed.
- *wait* - Added and indicates how long the caller is blocked on calls.
- *timeout* - Replaced by *ttl*.
- *ttl* - Added and replaces *timeout*. Strictly applies to request (and message) TTL.
- *ctag* - Replaced by *reply*.
- *reply* - Replaces *ctag* and is an AMQP address that specifies where RMI replies are sent.
- *any* - Removed and replaced by *data*.
- *data* - User defined data that is round-tripped back to the caller. Replaces *any*.
- *transport* - Replaced with rich protocol handlers supported by the URL.

Plugin (class) changes
----------------------

All accessor methods replaced with *@property* and appear as attributes.

Here are a few major methods affected:

- enabled()
- get_uuid()
- get_url()
- get_cfg()


gofer 2.1
^^^^^^^^^

Not Released.

gofer 2.2
^^^^^^^^^

Not Released.

gofer 2.3
^^^^^^^^^

Notes:

- Support for custom AMQP exchanges added. This includes an additional *exchange* option
  passed by callers to indicate the exchange to be used for temporary queues used for
  synchronous replies. For plugins, the descriptor was augmented to support an *exchange*
  property in the [messaging] section.

gofer 2.4
^^^^^^^^^

Notes:

 - AMQP Message durability fixed in python-amqp adapter.

 - Added support for plugin descriptor properties that specifies the level to which
   the agent manages the broker model. Specifically, how the agent manages its
   request queue. The ``[messaging]`` *exchange* property was replace by support in the
   new [model] section documented below. See: descriptor documentation for details.

 - Thread pool distribution fixed so that idle worker threads are selected when available.

 - The python-amqplib AMQP library is no longer supported. It was redundant to support
   for python-amqp which is better maintained and widely available. This means that the
   python-gofer-amqplib package is no longer provided. Further that, AMQP-0-8 is no longer
   supported. This functionality can be resurrected on community request.

 - The *amqp* adapter (python-amqp) updated to use EPOLL and basic_consume() instead of
   using dynamic polling and basic_get().

 - By default, the proxy (caller) will no longer declare the agent queue. Since the *address*
   really specifies AMQP routing (exchange/queue), gofer cannot assume the queue name
   or properties. The agent declaration and binding is the responsibility of the agent
   or the (caller) application.
   
 - The *qpid* adapter enables qpid heartbeat option on connections.

Added ``[model]`` section with the following properties:

- *managed* - Defines level of broker model management.
- *queue* - The name of the request queue.
- *exchange* - An (optional) exchange. The exchange is not declared/deleted.


gofer 2.5
^^^^^^^^^

Notes:

 - Added the python-gofer-proton messaging adapter. The adapter supports AMQP 1.0
   and use the Apache Qpid ``proton`` library.

 - The gofer.messaging.Exchange and gofer.messaging.Queue now support an additional
   ``url`` parameter which is used when ``url`` is not passed to specific method.

 - NotFound raised when an AMQP node (queue) does not exist.  See messaging.adapter.model
   for details on affected methods.

Deprecated:

 - Using gofer.proxy.agent() has been deprecated.


gofer 2.6
^^^^^^^^^

Notes:

 - Fixed recursion issue in proton adapter reconnect logic.

 - Add support for dynamic plugin loading, reloading and unloading.

 - Add plugin monitoring.  When enabled in agent.conf, the agent container will monitor
   the /etc/gofer/plugins directory for changes to plugin descriptors.  When a descriptor
   has changed, the plugin is reloaded.  When a *new* descriptor is found, the plugin is
   loaded.  When a plugin descriptor is deleted, the plugin is unloaded.
   See [main] *monitor* property in agent.conf.

 - Decentralized RMI scheduling.  Each plugin has its own scheduler.

 - Add support for RMI request forwarding to other plugins.  Requests can be forwarded
   to other plugins when they cannot be satisfied by the target plugin.
   See [main] *accept* and *forward* properties for details.

 - Much better AMQP connection management.  When plugins are unloaded, all associated
   AMQP connections are closed.

 - Add services API to the *system* plugin.  The *Service* class supports *start*,
   *restart*, *stop* and *status* operations on services.

 - The python-gofer-qpid package *Requires:* python-ssl.  Needed so that python-qpid
   will support SSL.

Deprecated:

 - The *maintenance window* feature and associated properties.


gofer 2.7
^^^^^^^^^

Notes:

- Add ``gofer`` command for interaction with goferd.  See: ``man gofer`` for
  details.  Packaged in gofer-tools.  See newly added `[management]` section
  of `/etc/pulp/agent.conf`.

- Plugin monitoring removed.  Use gofer.agent.PluginContainer.load()
  and gofer.agent.PluginContainer.unload() instead.

- Added ``@load`` and ``@unload`` decorators.  Plugins can participate in
  plugin loading and unloading.

- The `package` plugin has been rewritten to shell out instead of using the
  yum library.  Much simpler.

- The gofer.rmi.shell module added.  This can be used by plugins to easily and
  consistently provide functionality when using external commands is needed.
  Supports cancellation, progress reporting and returns stdout and stderr.
  The *system* and *package* plugins converted to use this.

- Improved debug logging in messaging adaptor reliability packages.
  This helps with troubleshooting AMQP issues.

- Added *latency* property to the `[main]` section of the plugin descriptor.
  Adding latency can be used for throttling and widening the request cancellation window.

- Canceled RMI requests discarded just prior to execution.  Plugin still responsible for
  canceling requests already in progress.

- Reference plugins no longer packaged.  The `test` plugin renamed to `demo` and
  not enabled by default.

- Dynamic plugin loading, reloading and unloading improved.

- As with every release, better unit test coverage.


Fixes:

- Minor memory leak fixed.  The leak was ~384 bytes per request.

- Fixes issue whereby locally stored requests are routed to a plugin that no
  longer specifies a URL.  The requests are discarded.

- AMQP connections used by plugin thread pool workers closed between requests.
  These connections can be idle/unused for long periods.  Closing them reduces
  the number of open network connections.

Deprecated:

- The ``uuid`` in the [messaging] section of the plugin descriptor has been
  deprecated.  Use [model] ``queue`` instead.

- The ``@initializer`` decorator has been deprecated.  Use ``@load`` instead.

- Authorization has been support. It will continue to support
  authentication.  This includes:
    - Shared secret.  The *secret* option in the @remote decorator.
    - The @pam decorator.
    - The @user decorator.
    - The *pam* property in the message.


gofer 2.8
^^^^^^^^^

Notes:

- Added support for RMI invocation models.  The ``direct`` model is the default and
  invokes the remote method within the ``goferd`` process.  This is the model used by
  <= 2.7.  The new ``fork`` model spawns a child process for each method invocation.
  Invoking the method in a separate process provides isolation and better cancellation
  behavior.  The isolation protects ``goferd`` against memory leaks and corruption
  potentially introduced by plugins (or code used by plugins). When using the ``fork``
  model, RMI cancellation is implemented by killing the child process.  As a result
  cancellation is certain and immediate regardless of whether cancellation is implemented
  by the method.  See: ``direct`` and ``fork`` decorators.

Fixes:

- Proton message sending reliability regression introduced in 2.7.


Deprecated:


gofer 2.9
^^^^^^^^^

Notes:

- Added ``direct`` and ``fork`` plugin decorators used to specify the RMI invocation model.
  Using one of these decorators is preferred to using the ``model=`` parameter to the
  ``remote`` decorator.

- Added memory profiler to metrics.

- Added context manager to Timer and associated decorator.

Fixes:

Deprecated:


gofer 2.10
^^^^^^^^^^

Notes:

- Added support for ``soft`` plugin shutdown. Mainly internal API enhancement but improves
  behavior of plugin ``unload`` and ``reload``. Both operations now do a ``soft`` shutdown by default.

- The thread-pool design improved.

Fixes:

- The ``hard`` plugin/thread-pool shutdown aborted threads which caused reply messages to silently
  never be sent.  Only affected  ``unload`` and ``reload`` operations.

Deprecated:


gofer 2.11
^^^^^^^^^^

Notes:

- Exit handler terminate threads.

Fixes:

- Fix compatibility python-amqp 2.1.4 Channel.wait().

Deprecated:


gofer 2.12
^^^^^^^^^^

Notes:

- Support python 2.7+ and 3.2+

- Python < 2.7 no longer supported.

Fixes:


Deprecated: