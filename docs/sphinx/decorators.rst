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

- **secret** - used to specify a *shared* secret that must be passed for authorization.
    - required: No
    - type: str|callable
    - default: None

@pam
----

The *pam* decorator is used to specify PAM authentication criteria for access to a function or class
method.  This additional authentication may be used in conjunction with shared secrets.

Options:

- **user** - specified user name.
    - required: Yes
    - type: str
    - default: n/a
- **service** - used to specify the PAM service to be used for the authentication.
    - required: No
    - type: str
    - default: passwd

@user
-----

The *user* decorator is used to specify PAM authentication criteria for access to a function or class
method.  This additional authentication may be used in conjunction with shared secrets.  This is an
alias for the @pam decorator.

Options:

- **name** - specified user name.
    - required: Yes
    - type: str
    - default: n/a
