

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

This adapter uses the ``proton`` library.

- *AMQP* - 1.0
- *package* - gofer.messaging.adapter.proton
- *provides*:
   - amqp-1-0
   - proton
   - qpid


python-amqp
^^^^^^^^^^^

This adapter uses the ``amqp`` library.

- *AMQP* - 0-9-1
- *package* - gofer.messaging.adapter.amqp
- *provides*:
   - amqp-0-9-1
   - rabbitmq
   - rabbit
