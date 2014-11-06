

Messaging Adapters
==================

Each adapter is a standardized integration with an external messaging library.
They are a specialized plugin that provides communication with message brokers
supported by the library.

Supported
---------

python-qpid
^^^^^^^^^^^

This adapter uses the ``qpid.messaging`` library.

- *AMQP* - 0-10
- *package* - gofer.messaging.adapter.qpid
- *provides*:
   - amqp-0-10
   - qpid.messaging
   - qpid


proton
^^^^^^

Coming soon.


python-amqplib
^^^^^^^^^^^^^^

This adapter uses the ``amqplib.client_0_8`` library.

- *AMQP* - 0-8
- *package* - gofer.messaging.adapter.amqplib
- *provides*:
   - amqp-0-8
   - rabbitmq


python-amqp
^^^^^^^^^^^

This adapter uses the ``amqp`` library.

- *AMQP* - 0-9-1
- *package* - gofer.messaging.adapter.amqp
- *provides*:
   - amqp-0-9-1
   - rabbitmq
