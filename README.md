Gofer
=====

Gofer provides an extensible, light weight, universal python agent. It has no
relation to the Gopher_ protocol.
The gofer core agent is a python daemon (service) that provides infrastructure
for exposing a remote API and for running Recurring Actions. The APIs contributed by
plugins are accessible by Remote Method Invocation (RMI). The transport for RMI is
AMQP using the QPID_ message broker. Actions are also provided
by plugins and are executed at the specified interval.

.. _Gopher: http://en.wikipedia.org/wiki/Gopher_%28protocol%29
.. _QPID: http://qpid.apache.org/

License: LGPLv2

Gofer provides:

- An agent (daemon)
- Plugin Container
- Remote access to API provided by plugins
- Action scheduling

Plugins provide:

- Remote API.
- Recurring (scheduled) actions
- Agent identity (optional)

.. image:: images/agent.png
