Ruby Examples
=============

Notes:
- The ruby API mirrors the python API almost exactly but with ruby semantics.
- The ruby API is mostly complete but not still under construction.
- As of 0.71+, ruby-gofer uses rubygem-qpid instead of ruby-qpid.
- rDocs are coming!

Synchronous Invocation
^^^^^^^^^^^^^^^^^^^^^^

Sample of server code invoking synchronously methods (remotely) on the agent.  This is the default
behaviour and the timeout is 90 seconds by default.

.. code-block:: ruby

 require 'rubygems'
 require 'rubygem-qpid'
 require 'gofer'

 agent = Gofer::Agent.new('jortel')

 # invoke methods on the agent (remotely)
 dog = agent.Dog.new()
 puts dog.bark('hello')
 puts dog.wag(3)
 puts dog.bark('hello')

 # methods that raise exceptions
 try:
    puts dog.notpermitted()
 rescue RemoteException=>e
    puts e
 end


Synchronous Invocation (specify timeout)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Sample of server code invoking synchronously methods (remotely) on the agent with a
timeout of 180 seconds.

.. code-block:: ruby

 require 'gofer'

 agent = Gofer::Agent.new('jortel', :timeout=>180)  # specify timeout

 # invoke methods on the agent (remotely)
 dog = agent.Dog.new()
 dog.bark('hello')
 dog.wag(3)
 dog.bark('hello')



Timeout can also be an *Array*: [<started>, <execute>] where the timeout specifies:

- Timeout for starting the operation
- Timeout for completing the operation.

In this example, we specify that the operation must be started by the agent within 3 seconds
and it must be completed within 180 seconds.

.. code-block:: ruby

 require 'gofer'

 agent = Gofer::Agent.new('jortel', :timeout=>[3,180])  # specify timeout

 # invoke methods on the agent (remotely)
 dog = agent.Dog.new()
 dog.bark('hello')
 dog.wag(3)
 dog.bark('hello')


Or, the timeout can be specified on the Dog (stub) constructor:

.. code-block:: ruby

 require 'gofer'

 agent = Gofer::Agent.new('jortel')  # specify timeout

 # invoke methods on the agent (remotely)
 dog = agent.Dog.new(:timeout=>[3,180])
 dog.bark('hello')
 dog.wag(3)
 dog.bark('hello')


Asynchronous (fire & forget) Invocation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Sample of server code invoking synchronously methods (remotely) on the agent.  This works the same for
asynchronous *fire-and-forget* where not reply is wanted.  Asynchronous invocation returns the serial
number of the request.

.. code-block:: ruby

 require 'gofer'

 #create an agent where consumerid = "jortel"
 agent = Gofer::Agent.new('jortel', :async=>true)

 # invoke methods on the agent (remotely)
 dog = agent.Dog()
 dog.bark('hello')
 dog.wag(3)
 puts dog.bark('hello')
    'e688f50b-3108-43dd-9a57-813f434749a8'

 # methods that raise exceptions
 try:
   print dog.sit()
 rescue Exception=>e
   puts e
 end

 try:
   print dog.notpermitted()
 rescue Exception=>e
   puts e
 end


Asynchronous (callback) Invocation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Sample of server code invoking asynchronously methods (remotely) on the agent.   The is the *callback*
form of asynchronous invocation.  This example uses a *Listener* class.   But, the *listener* can also
be any *callable*. Asynchronous invocation returns the serial number of the request to be used by
the caller to further correlate request & response.

.. code-block:: ruby

 require 'gofer'
 require 'gofer/messaging/async/ReplyConsumer'

 # specify a correlation tag to be used to correlate the responses.

 ctag = 'tasks'

 # create my listener class

 class Listener:

  #  Succeeded notification.
  #  reply:
  #      sn - request serial number.
  #      origin - the reply sender.
  #      retval - request returned value.
  #      any - user defined data (round tripped)
  def succeeded(reply)
  end

  # Failed (exception raised) notification.
  #   reply:
  #     sn - request serial number.
  #     origin - the reply sender.
  #     exval - the raised exception.
  #     any - user defined data (round tripped)
  def failed(reply)
  end

  #Request status changed notification.
  # reply:
  #    sn - request serial number.
  #    origin - the reply sender.
  #    status - the new request status.
  #    any - user defined data (round tripped)
  def status(reply):
  end

 # create my reply consumer using the correlation tag and
 # my listener

 reader = ReplyConsumer.new(tag)
 reader.start(Listener.new())

 #create an agent where consumer ID = "jortel" and
 # setup for asynchronous invocation with my correlation tag.   The async=True
 # not needed because a ctag was specified.

 agent = Gofer::Agent.new('jortel', :ctag=>tag)

 # invoke methods on the agent (remotely)
 dog = agent.Dog.new()
 dog.bark('hello')
 dog.wag(3)
 puts dog.bark('hello')
    'e688f50b-3108-43dd-9a57-813f434749a8'


Asynchronous (group) Invocation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Invoking operations on multiple agents is asynchronous by nature.  This can be done by simply creating
an agent (proxy) with a collection (list|tuple) of ids instead of just one.  Basically, it's the same
as the asynchronous examples above except that when more then (1) id is specified, method invocations
return a list of tuples (id, serial number) instead of just the serial number.

Eg:

.. code-block:: ruby

 require 'gofer'

 #create an agent with a list of consumer ids.
 group = ['a', 'b', 'c']
 agent = Gofer::Agent.new(group, :ctag=>'tasks')
 dog = agent.Dog.new()
 puts dog.wag(10) # request sent to (a,b,c) and asynchronous replies sent to 'tasks' queue.
   [{:uuid=>'a', :sn=>'e688f50b-3108-43dd-9a57-813f434749a8'}, {:uuid=>'b', :sn=>'e4e60889-edac-42f1-8b64-443dbe693566'}, {:uuid=>'c', :sn=>'95960889-edac-42f1-8b64-443dbe693f23']]


Maintenance Windows
^^^^^^^^^^^^^^^^^^^

Asynchronous invocation can define a *window* in which the agent must perform the operation.
This is intended to support *maintenance windows* but can be used for:

#. Asynchronous w/ timeout
#. Asynchronous to be performed in the future
#. 1 & 2.
 
In cases where the agent cannot perform the operation within the specified *window*, a *!WindowMissed*
exception is raised. In this example, we tell agents (a,b,c) dogs to wag their tails 10 times on
July 26th between 10am & 11am.  This time the *ctag* and *window* will be defined on the *Dog.new()*
just to demonstrate that it may be done.

Eg:

.. code-block:: ruby

 require 'gofer'

 #create an agent with a list of consumer ids.
 # window is on July 26th between 10am - 11am.
 group = ['a', 'b', 'c',]
 start = Time.utc(2010, 'jan', 26, 10)
 maint = Window.new(:begin=>start, :hours=>1)
 agent = Gofer::Agent(group)
 dog = agent.Dog.new(:ctag=>'tasks', :window=>maint)
 puts dog.wag(10) # request sent to (a,b,c) and asynchronous replies sent to 'tasks' queue.
   [{:uuid=>'a', :sn=>'e688f50b-3108-43dd-9a57-813f434749a8'}, {:uuid=>'b', :sn=>'e4e60889-edac-42f1-8b64-443dbe693566'}, {:uuid=>'c', :sn=>'95960889-edac-42f1-8b64-443dbe693f23']]

