Options
=======

The RMI options can be passed to the proxy.agent() function and the Agent or Stub constructor.
When options passed to either the proxy.agent() or Agent constructor, they apply to all RMI
calls unless they are overridden in the Stub constructor.

These options are as follows:

Summary
^^^^^^^

 *reply*
   The asynchronous RMI reply address.  Eg: amq.direct/test-queue
 *trigger*
   Specifies trigger used for RMI calls. (0=auto <default>, 1=manual)
 *ttl*
   The TTL (seconds) for the agent to accept the RMI request.
 *wait*
   The time (seconds) to wait (block) for a result.
 *progress*
   A progress callback specified for synchronous RMI. Must have signature: fn(report).
 *authenticator*
   A subclass of pulp.messaging.auth.Authenticator that provides message authentication.
 *data*
   User defined data associated with the RMI request and is round-tripped.
   

Details
^^^^^^^

reply
-----

The **reply** option specifies the reply address.  When specified, it implies all requests
are asynchronous and that all replies are sent to the AMQP address.

Example: Assume a reply listener on the topic or queue named: "foo":

Passed to Agent() and apply to all RMI calls.

::

 from gofer.proxy import Agent

 agent = Agent(url, uuid, reply='foo')


trigger
-------

The **trigger** option specifies the *trigger* used for asynchronous RMI.
When the trigger is specified as *manual*, the RMI calls return a *trigger*
object instead of the request serial number.
Each trigger contains a **sn** (serial number) property that can be used for reply correlation.
The trigger is *pulled* by calling the trigger as: *trigger()*.

Trigger values:

- **0** = Automatic *(default)*
- **1** = Manual

Passed to Agent() and apply to all RMI calls.

::

 from gofer.proxy import Agent

 agent = Agent(uuid, trigger=1)
 dog = agent.Dog()
 trigger = dog.bark('delayed!')
 print trigger.sn      # do something with serial number
 trigger()             # pull the trigger


ttl and wait
------------

The **ttl** option is used to specify the RMI call lifespan. The *ttl* is the time in seconds
for the agent to *accept* the request.  The message TTL (time-to-live) is set to the *ttl* for both
synchronous and asynchronous RMI calls.  Additionally, for synchronous RMI, the caller is blocked for
the number of seconds specified in the *wait* option.  The default *timeout* is 10 seconds and the
default *wait* for synchronous RMI is 90 seconds. A *wait=0* indicates that the stub should not
block and wait for a reply.

The *timeout* and *wait* can be a string and supports a suffix to define the unit of time.
The supported units are as follows:

- **s** : seconds
- **m** : minutes
- **h** : hours
- **d** : days

Passed to Agent() and apply to all RMI calls.

::

 from gofer.proxy import Agent

 # TTL 5 seconds
 agent = Agent(url, uuid, ttl=5)

 # TTL 5 minutes
 agent = Agent(url, uuid, ttl=5m)

 # TTL 30 seconds, wait for 5 seconds
 agent = Agent(url, uuid, ttl=30, wait=5)
