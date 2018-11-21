Gofer
=====

![travis](https://travis-ci.org/jortel/gofer.svg?branch=master)

Gofer provides an extensible, light weight, universal python agent. It has no
relation to the [Gopher](http://en.wikipedia.org/wiki/Gopher) protocol.
The gofer core agent is a python daemon (service) that provides infrastructure
for exposing a remote API and for running Recurring Actions. The APIs contributed by
plugins are accessible by Remote Method Invocation (RMI). The transport for RMI is
AMQP using a message broker. Actions are also provided by plugins and are executed at
the specified interval.

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

![agent](https://raw.github.com/jortel/gofer/master/docs/sphinx/images/agent.png)


Documentation
-------------

Documentation can be found [here](http://gofer.readthedocs.org/en/latest/)

Community
---------

Maintainer: Jeff Ortel (jortel@redhat.com)

IRC: #gofer on irc.freenode.net

Mailing List:
- mailto: gofer@lists.fedorahosted.org
- subscribe: [here](https://fedorahosted.org/mailman/listinfo/gofer)


Fedora
------

The Gofer project originally started in [Fedora Hosted](https://fedorahosted.org/gofer/) and is available 
in [Fedora](http://fedoraproject.org/) and [EPEL](http://fedoraproject.org/wiki/EPEL) distributions.
Gofer can also be installed from [Copr](https://copr.fedorainfracloud.org/coprs/jortel/gofer/)
repositories.

