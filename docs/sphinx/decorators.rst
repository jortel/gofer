Plugin Decorators
=================


Decorators for remote methods/functions provided by plugins.  All decorators may be stacked.

@action
-------

The *action* decorator is used to designate a function or class method to treated as
a recurring action.

Options:

- **interval** (one of):
   - days
   - seconds
   - minutes
   - hours
   - weeks
- required: Yes
- type: int
- default: n/a

@remote
-------

The *remote* decorator is used to designate a function or class method as being remotely accessible.

Options:

- **model** - the RMI execution model (direct|fork).
  The *fork* model spawns a child process for each method invocation.
    - required: No
    - type: str
    - default: direct
    - note: Added in 2.8


@direct
-------

The *direct* decorator is used to designate a function to use the *direct* invocation model.
With this model, the function is invoked within the goferd process.

Added: 2.8


@fork
-----

The *fork* decorator is used to designate a function to use the *fork* invocation model.
With this model, the function is invoked in a newly spawned child process.  This model may be used
to insulate the goferd process from unwanted side effects such as memory and filedes leaks,
global configuration changes and core dumps.

Added: 2.8
