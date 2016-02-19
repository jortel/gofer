Design
======

Approach
^^^^^^^^

The preferred approach is to leverage a Message Bus and possibly a Messaging Framework
that uses the message bus for transport. The advantages over home grown and/or
point-to-point solutions are as follows:

- Hub and Spoke topology. Each node knows the address of the broken but not each other.
- Key-based routing. Nodes are associated with properties instead of IP addresses.
- Reliable message delivery.
- Message queueing.
- Automatic reconnect behaviour.
- And probably others ...

.. image:: images/topology.png

Dispatch Architecture:

.. image:: images/dispatch.png


Messaging
^^^^^^^^^

A Messaging Framework provides RMI (Remote Method Invocation) & Event semantics on top of messaging.
This gives application developers an easy to use abstraction and hides some of the complexities of
exchange and dispatching. Especially in OO applications, invoking a method remotely on an agent
without regard for message exchange and routing enhances reliability and productivity.

Requirements Summary:

- Key-based routing based on consumer ID.
- Synchronous RMI.
- Asynchronous RMI.
- Fire and Forget
- Callbacks
- Returned values.
- Exception propagation.
- Easy to use.
- Easy to extend classes/method exposed for RMI.
- Events
- Support multiple API versions.

Synchronous RMI:
----------------

.. image:: images/sync.png

Asynchronous RMI:
-----------------

.. image:: images/async.png


Messages
--------

The message format is json:

- Security-Wrapper:
   - **signature**  - A base64 encoded signature.
   - **message**    - A json message with stricture of: (Request | Result | Exception)

- Envelope:
   - **sn**         - Serial Number (uuid).
   - **version**    - The API version.
   - **routing**    - A tuple containing the amqp (sender, destination).
   - **secret**     - The (optional) shared secret used for request authentication. **DEPRECATED** in 2.7.
   - **pam**        - The (optional) PAM authentication credentials. **DEPRECATED** in 2.7.
   - **replyto**    - The reply amqp address (optional).
   - **expiration** - An (optional) ISO-8601 expiration.
   - one of
      - **request** - An RMI request. See: Request.
      - **result**  - An RMI result. Has value of: (Result | Exception).
      - **status**  - An RMI request status report.  See: Status.
   - **timestamp**  - An ISO-8601 reply timestamp (UTC).
   - **data**       - User defined data.

- Request(Envelope):
   - **classname**  - The target class name.
   - **cntr**       - The (optional) remote class constructor arguments. format: ([],{}).
   - **method**     - The target instance method name.
   - **args[]**     - The list of parameters passed to method
   - **kws{}**      - The named keyword arguments passed to method.

- Status(Envelope):
   - **status**     - A request status with value of
      - *accepted*  - Accepted by the agent and queued.
      - *rejected*  - Rejected by the agent.
      - *started*   - The request has started execution.
      - *progress*  - Progress is begin reported.  See: Progress.

- Progress(Status):
   - **total**      - The total number of items to be completed.
   - **completed**  - The number of items completed.
   - **details**    - Reported details.  Can be anything.

- Result(Envelope):
   - **retval**     - The returned data.  Can be anything.

- Exception(Envelope)
   - **exval**      - The formatted exception (including trace).
   - **xmodule**    - The exception module name.
   - **xclass**     - The exception class.
   - **xstate**     - The exception state.  Contains the exception __dict__.
   - **xargs**      - The exception *args* attribute when subclass of *Exception*.


Example RMI request message:

::

 {
    "sn": "e7e91fb6-611b-4284-a9ed-ac1636b2c709",
    "routing": [
        "cfa806a4-919a-495f-b1dd-3fc11be9a8d0" ,
        "19802a28-a18c-4ae3-ac57-b7a2e78a427a"
    ],
    "replyto": "cfa806a4-919a-495f-b1dd-3fc11be9a8d0",
    "version": "0.2"
    "request": {
        "classname": "Dog",
        "method": "bark"
        "args": ["hello"],
        "kws": {}
    }
 }

Example reply:

::

 {
    "sn": "e7e91fb6-611b-4284-a9ed-ac1636b2c709",
    "version": "0.2",
    "result": {
        "retval": "Yes master.  I will bark because that is what dogs do."
    }
 }


Example status reply:

::

 {
    "origin": "123",
    "status": "accepted",
    "version": "0.2",
    "sn": "985cb165-d291-47de-ab34-ecb20895384e",
    "data": "group 2"
 }

