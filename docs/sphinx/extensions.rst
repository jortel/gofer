
Plugin Extension
================

As gofer plugins are written and shared throughout the open source community, it seems likely that
rather than writing your plugin from scratch, it would be useful to be able to extend one that already
exists. Plugins have an API for extending their *remote* API with *remote* objects provided by other
plugins.  Plugin extension can also be specified in the plugin *descriptor* using the *extends*
property


Extending
^^^^^^^^^

What can be imported:

- class object
- function object


**Using the descriptor property:**


Example:

plugin: **dog** can extend the **animals** plugin.  Using this method will add all of the *dog* API
to the *animals* API.

::

 [main]
 enabled=1
 extends=animals


**Using the API:**


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

 animals = Plugin.find('animals')
 plugin = Plugin.find(__name__)

 # just import Dog
 plugin += animals['Dog']

 # import everything
 plugin += animals


Inheritance
^^^^^^^^^^^

Imported class objects may be used as if imported using the standard *import* directive.  When used
as a *superclass*, the inherited methods will be exposed (@remote) as decorated in the superclass.

Examples:

::

 from gofer.agent.plugin import Plugin

 # import Dog from animals plugin

 animals = Plugin.find('animals')
 Dog = animals['Dog']

 class Retriever(Dog):
    @remote
    def fetch(self):
        pass


Results in the following *remote* API:

Retriever:

- bark()
- fetch()


Delegation
^^^^^^^^^^

In many cases, plugins may choose to leverage imported objects by delegation rather than inheritance.

In this example, the Old McDonald toy does not extend *Dog* but rather delegates the functionality
of a dog bark() to an instance of Dog:

::

 from gofer.agent.plugin import Plugin

 # import Dog from animals plugin

 animals = Plugin.find('animals')
 Dog = animals['Dog']

 # Old McDonald toy
 class Toy:
    @remote
    def theDog(self):
        dog = Dog()
        dog.bark()

