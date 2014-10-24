

Messaging Providers
===================

Each provider is a standardized integration with an external messaging library.
They are a specialized plugin that provides communication with message brokers
supported by the library.

Supported
---------

python-qpid
^^^^^^^^^^^

This provider uses the ``qpid.messaging`` library.

- *AMQP* - 0-10
- *package* - gofer.messaging.provider.qpid
- *provides*:
   - amqp-0-10
   - qpid.messaging
   - qpid


proton
^^^^^^

Coming soon.


python-amqplib
^^^^^^^^^^^^^^

This provider uses the ``amqplib.client_0_8`` library.

- *AMQP* - 0-8
- *package* - gofer.messaging.provider.amqplib
- *provides*:
   - amqp-0-8
   - rabbitmq


python-amqp
^^^^^^^^^^^

This provider uses the ``amqp`` library.

- *AMQP* - 0-9-1
- *package* - gofer.messaging.provider.amqp
- *provides*:
   - amqp-0-9-1
   - rabbitmq
