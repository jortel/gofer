
import os

from mock import Mock

from gofer.rmi.process import Thing
from gofer.agent.rmi import Context

context = Context.current()
context.progress = Mock()
context.cancelled = Mock(return_value=False)

t = Thing(os)
print t.listdir('.')