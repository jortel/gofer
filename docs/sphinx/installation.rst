Installation
============

Packages
^^^^^^^^

Gofer is packaged into RPMs for Linux.  These packages are as follows:

- **gofer** - The gofer agent (goferd).
- **python-gofer** - The common library.
- **python-gofer-qpid** - The python-qpid messaging adapter.
- **python-gofer-amqp** - The python-amqp messaging adapter.

Depending on system capabilities, the *gofer* package registers goferd
with systemd or upstart service managers.

python optimizations
--------------------

By default, goferd runs python with optimizations enabled. If you want to disable those
optimizations, this can be done by altering the environment file for this service,
``/etc/sysconfig/goferd``, and setting the value of PYTHONOPTIMIZE to zero:
``PYTHONOPTIMIZE=0``

Development
^^^^^^^^^^^

The gofer project is hosted by Github.  To install from source, you must first clone the
git repository.  The python library can be installed using something like pip.  Once installed,
the goferd daemon can be installed.

Cloning the repository::

 $ git clone https://github.com/jortel/gofer.git


In the examples below, *<git>* is the directory containing the cloned repository.

Files can be link or copied.

goferd
------

To install goferd::

 # cp <git>/gofer/bin/goferd /usr/bin


systemd
-------

To register goferd with systemd::

 # cp <git>/gofer/usr/lib/systemd/system/goferd.service /usr/lib/systemd/system


upstart
-------

To register goferd with upstart::

 # cp <git>/gofer/etc/init.d/goferd /etc/init.d
 # chkconfig --add goferd

