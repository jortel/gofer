
Plugin Extension
================

As gofer plugins are written and shared throughout the open source community, it seems likely that
rather than writing your plugin from scratch, it would be useful to be able to extend one that already exists.
To support this, the gofer plugin manager provides a mechanism to export objects from one plugin and
import them into another.  This is both convenient and necessary due to annotation processing side affects
and PYTHONPATH limitations.

Since *remote* methods/functions can already be shared across UUIDs, it is assumed that a plugin
would import objects from another plugin to:

- Extend the functionality
- Alter the manner in which the functionality is exposed as *remote*.
   - Different authentication/authorization
   - shared vs. not shared
- obscure (hide) some of the API

In many cases, the natural aggregation of the API provided by installed and enabled plugins
produces the desired agent functionality.  However, this is not always the case and it may be desirable
to provide functionality of a plugin by extension.  The strategy for extending other plugins is to
install the plugin you wish to extend.  Leave that plugin *disabled*.  Reference it as *required* by
your plugin.  Then, import the functionality provided by the other plugin into yours as use as needed.
Importing from *enabled* plugins is permitted but be careful of unwanted API related side effects.

Importing
^^^^^^^^^

Steps to import and object (or function) from another plugin:

#. get a reference to the plugin
#. export the object by name (class name, function name) and assign to a local variable.

What can be imported:

- class object
- function object

Example:

plugin: **animals**

::

 class Dog:
    @remote
    def bark(self):
        pass


plugin: **myplugin**

::

 from gofer.agent.plugin import Plugin

 # import Dog from animals plugin
 animals = Plugin.find('animals')
 Dog = animals.export('Dog')


Inheritance
^^^^^^^^^^^

Imported class objects may be used as if imported using the standard *import* directive.  When used
as a *superclass*, the inherited methods will be exposed (@remote) as decorated in the superclass.
Though, in most cases, where importing is used, it will be desirable to re-decorate methods to redefine
their properties.

Examples:

::

 from gofer.agent.plugin import Plugin

 # import Dog from animals plugin
 animals = Plugin.find('animals')
 Dog = animals.export('Dog')

 class Retriever(Dog):
    @remote(secret='wagf')
    def fetch(self):
        pass


Results in the following *remote* API:

Retriever:

- bark()
   - auth: *None*
- fetch()
   - auth: *shared secret*

However, notice that the *auth* on the inherited bark() is different than fetch().
To change this, simply override the method and re-decorate as needed:

::

 from gofer.agent.plugin import Plugin

 # import Dog from animals plugin
 animals = Plugin.find('animals')
 Dog = animals.export('Dog')

 class Retriever(Dog):

    @remote(secret='wag')
    def bark(self):
        Dog.bark(self)

    @remote(secret='wag')
    def fetch(self):
        pass


Delegation
^^^^^^^^^^

In many cases, plugins may choose to leverage imported objects by delegation rather than inheritance.

In this example, the Old McDonald toy does not extend *Dog* but rather delegates the functionality
of a dog bark() to an instance of Dog:

::

 from gofer.agent.plugin import Plugin

 # import Dog from animals plugin
 animals = Plugin.find('animals')
 Dog = animals.export('Dog')

 # Old McDonald toy
 class Toy:
    @remote
    def theDog(self):
        dog = Dog()
        dog.bark()


Limitations
^^^^^^^^^^^

- Only classes and function may be exported/imported.
- The Plugin.export() is designed to support extension.  See [1] & [2].

**[1]** For imported (remote) functions to be visible (as remote) in plugin module, the
importing module (plugin) must have at least 1 function decorated with @remote.

Eg: *fn()* not included as *remote* API for the plugin:

::

 fn = plugin.export('fn')


But, now it will:

::

 fn = plugin.export('fn')

 @remote
 def foo(): pass



**[2]** For remote methods of imported classes to be visible (as remote) in subclasses,
the subclsss must have at least 1 method decorated with @remote.

Eg: *bark()* not included as *remote* in class Dog for the plugin:

::

 Dog = plugin.export('Dog')
 class Retriever(Dog):
    pass


But, now it will:

::

 Dog = plugin.export('Dog')
 class Retriever(Dog):
    @remote
    def wag(self):
        pass

