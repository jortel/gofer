Options
=======

The RMI options can be passed to the proxy.agent() function and the Agent or Stub constructor.
When options passed to either the proxy.agent() or Agent constructor, they apply to all RMI
calls unless they are overridden in the Stub constructor.

These options are as follows:

Summary
^^^^^^^

 *async*
   The asynchronous RMI flag
 *ctag*
   The asynchronous RMI reply correlation tag
 *trigger*
   Specifies trigger used for RMI calls. (0=auto <default>, 1=manual)
 *winndow*
   RMI processing window
 *secret*
   The shared secret (security)
 *timeout*
   The timeout (seconds) for the agent to accept the RMI request.
 *wait*
   The time (seconds) to wait for a result using the synchronous policy.
 *progress*
   A progress callback specified for synchronous RMI. Must have signature: fn(report).
 *user*
   A user (name), used for PAM authenticated access to remote methods.
 *password*
   A password, used for PAM authenticated access to remote methods.
 *authenticator*
   A subclass of pulp.messaging.auth.Authenticator that provides message authentication.
   

Details
^^^^^^^
   
async
-----

The **async** option indicates that RMI requests are asynchronous.  The default is *False*.

Passed to proxy.agent() and apply to all RMI calls.

::

 from gofer import proxy

 agent = proxy.agent(uuid, async=True)


Passed to Agent() and apply to all RMI calls.

::

 from gofer.proxy import Agent

 agent = Agent(uuid, async=True)


Passed to stub constructor and apply only to calls to this stub.  Assume a class named *Dog*:

::

 from gofer import proxy

 agent = proxy.agent(uuid)
 dog = agent.Dog(async=True)



ctag
----

The **ctag** option specifies the asynchronous *correlation tag*.  When specified, it implies all requests
are asynchronous and that all replies are sent to the AMQP destination (topic or queue) named *ctag*.
The *async* option can also be specified but is redundant when specifying the *ctag* option.

Example: Assume a reply listener on the topic or queue named: "foo":

Passed to proxy.agent() and apply to all RMI calls.

::

 from gofer import proxy

 agent = proxy.agent(uuid, ctag='foo')


Passed to Agent() and apply to all RMI calls.

::

 from gofer.proxy import Agent

 agent = Agent(uuid, ctag='foo')


Passed to stub constructor and apply only to calls to this stub.  Assume a class named *Dog*:

::

 from gofer import proxy

 agent = proxy.agent(uuid)
 dog = agent.Dog(ctag='foo')


trigger
-------

The **trigger** option specifies the *trigger* used for asynchronous RMI.  Like, *ctag*, implies RMI is
to be asynchronous.  When the trigger is specified as *manual*, asynchronous RMI calls return a *trigger*
object instead of the request serial number.  In the case of *broadcast*, a list of triggers is returned.
Each trigger contains a **sn** (serial number) property that can be used for reply correlation.
The trigger is *pulled* by calling the trigger as: *trigger()*.

Trigger values:

- **0** = Automatic *(default)*
- **1** = Manual

Passed to proxy.agent() and apply to all RMI calls.

::

 from gofer import proxy

 # single shot
 agent = proxy.agent(uuid, trigger=1)
 dog = agent.Dog()
 trigger = dog.bark('delayed!')
 print trigger.sn      # do something with serial number
 trigger()             # pull the trigger

 # broadcast
 agent = proxy.agent([uuid,], trigger=1)
 dog = agent.Dog()
 for trigger in dog.bark('delayed!'):
     print trigger.sn  # do something with serial number
     trigger()         # pull the trigger


Passed to stub constructor and apply only to calls to this stub.  Assume a class named *Dog*:

::

 from gofer import proxy

 #single shot
 agent = proxy.agent(uuid)
 dog = agent.Dog(trigger=1)
 trigger = dog.bark('delayed!')
 print trigger.sn      # do something with serial number
 trigger()             # pull the trigger

 # broadcast
 agent = proxy.agent([uuid,])
 dog = agent.Dog(trigger=1)
 for trigger in dog.bark('delayed!'):
     print trigger.sn  # do something with serial number
     trigger()         # pull the trigger


window
------

The **window** specifies an RMI execution window.  This window is a date/time in the future in which
the agent should process the RMI.  The default is: *anytime*.

See: Window for details.

Example:

Assume the following window is created as between 10 and 20 seconds from now.

::

 from datetime import datetime as dt

 begin = later(seconds=10)
 window = Window(begin=begin, minutes=10)


Passed to proxy.agent() and apply to all RMI calls.

::

 from gofer import proxy

 agent = proxy.agent(uuid, window=window)


Passed to Agent() and apply to all RMI calls.

::

 from gofer.proxy import Agent
 from gofer.rmi.window import Window

 agent = Agent(uuid, window=window)


Passed to stub constructor and apply only to calls to this stub.  Assume a class named *Dog*:

::

 from gofer import proxy

 agent = proxy.agent(uuid)
 dog = agent.Dog(window=window)


secret
------

The **secret** option is used to provide *shared secret* credentials to each RMI call.  This option is
only used for agent plugin RMI methods where a *secret* is specified as required.

Examples: Assume the agent has a plugin with methods decorated with a secret='foobar'

Passed to proxy.agent() and apply to all RMI calls.

::

 from gofer import proxy

 agent = proxy.agent(uuid, secret='foobar')


Passed to Agent() and apply to all RMI calls.

::

 from gofer.proxy import Agent

 agent = Agent(uuid, secret='foobar')


Passed to stub constructor and apply only to calls to this stub.  Assume a class named *Dog*:

::

 from gofer import proxy

 agent = proxy.agent(uuid)
 dog = agent.Dog(secret='foobar')


timeout and wait
----------------

The **timeout** option is used to specify the RMI call timeout. The *timeout* is the time in seconds
for the agent to *accept* the request.  The message TTL (time-to-live) is set to the *timeout* for both
synchronous and asynchronous RMI call.  Additionally, for synchronous RMI, the caller is blocked for
the number of seconds specified in the *wait* option.  The default *timeout* is 10 seconds and the
default *wait* for synchronous RMI is 90 seconds.

In 0.75+, the *timeout* and *wait* can be a string and supports a suffix to define the unit of time.
The supported units are as follows:

- **s** : seconds
- **m** : minutes
- **h** : hours
- **d** : days

Passed to proxy.agent() and apply to all RMI calls.

::

 from gofer import proxy

 # 5 seconds
 agent = proxy.agent(uuid, timeout=5)

 # timout 5 minutes
 agent = proxy.agent(uuid, timeout=5m)

 # timeout 30 seconds, wait for 5 seconds
 agent = proxy.agent(uuid, timeout=30, wait=5)


Passed to Agent() and apply to all RMI calls.

::

 from gofer.proxy import Agent

 # timeout 10 seconds
 agent = Agent(uuid,  timeout=10)


Passed to stub constructor and apply only to calls to this stub.  Assume a class named *Dog*:

::

 from gofer import proxy

 # timeout 10 seconds
 agent = proxy.agent(uuid)
 dog = agent.Dog(timeout=10)



user/password
-------------

The **user** and **password** options are used to provide PAM authentication credentials to each RMI call.
This option is only used for agent plugin RMI methods decorated with @pam or @user.
This is really just a short-hand for the **pam** option.

Examples: Assume the agent has a plugin with methods decorated with @pam(user='root')

Passed to proxy.agent() and apply to all RMI calls.

::

 from gofer import proxy

 agent = proxy.agent(uuid, user='root', password='xxx')


Passed to Agent() and apply to all RMI calls.

::

 from gofer.proxy import Agent

 agent = Agent(uuid, user='root', password='xxx')


Passed to stub constructor and apply only to calls to this stub.  Assume a class named *Dog*:

::

 from gofer import proxy

 agent = proxy.agent(uuid))
 dog = agent.Dog(user='root', password='xxx')

