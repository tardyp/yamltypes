Yamltypes
==========

Tools for loading and validating yaml config files.

package is shipped with 2 entry points scripts:

* yamlconfig: This tool can validate a yaml file against its spec.

    The spec file can be either automatically found given the filename or given as parameter with ``--meta``

* yaml2rst: This tool automatically creates a rst documentation of the types defined in a directory.


Yamltypes module
=================

A common problem for the complex CI system developer is to separate
its configuration logic from its configuration data.

- Logic is the configuration of the builder, what does it build,
  what are the buildsteps, etc
- Data is the parameter you want to easily change in the day to day
  maintainance work. What are the slaves, and their capabilities?
  What branches are needed to be tracked? under what conditions? etc

YamlConfig helps to resolve this problem by providing tools to create
and describe a set of yaml files that are used as input for your master.cfg

Originally made for buildbot configuration, the spec format it defines can
be used to describe any kind of json compatible data.


Each parsed yaml file can be given a ``.meta.yaml`` file that acts as a
schema file describing what is allowed in the file, and potencially how to
present it in an edition UI.

.. _Meta-File-Format:

``.meta.yaml`` file Format
---------------------------

the meta yaml file is a yaml file made of nested dicts, describing the type
of data the type checker is waiting for.

Root Node
`````````
the meta yaml file must describe the ``root`` type, which will snowball
all the nested type checks

.. code-block:: yaml

    root:
      type: dict
      kids:
         param1:
         type: int
         param2:
         type: string

will match:

.. code-block:: yaml

    param1: 1
    param2: stringvalue

imports Node
`````````````

The meta yaml file can use types described in another file. For that, it will import
a list of ``.types.yaml`` files.

A ``.types.yaml`` is a yaml file defining a map of named types. ex:

.. code-block:: yaml

    foo:
        type: string
        values: [bar]

can be used in a ``myconfig.meta.yaml``:

.. code-block:: yaml

    imports:
        - foo.type.yaml
    root:
        type: dict
        kids:
            foo:
                type: listoffoos

Base types
``````````
base types are:

int
  an integer

string
  a string

boolean
  a true/false boolean

float
  a floating point number

Compound types
``````````````
A value of compound type is composed of several subtypes values or key/value:

dict
  an associative array that has a defined list of childrens key

map
  an associative array that has an arbitrary list childrens keys

list
  a list of arbitrary values

set
  a list that ensure member unicity (you cannot have several time the same value)

Specifying types of values
``````````````````````````
For ``map``, ``list``, ``set``, it is possible to specify what type is expected
as the values. The syntax is:

.. code-block:: yaml

   type: <compound_type>of<type>s

for example, following types are valid

.. code-block:: yaml

   type: mapofstrings
   type: listofints
   type: listofsetsofints

User defined types
``````````````````
You can specify a meta.yaml file defining the map of types, you can reuse inside your
main meta.yaml file. e.g:

.. code-block:: yaml

    location:
        type: string
        values: [l1,l2,l3,l4,l5,l6]

This defines a ``location`` type, which is a string with 6 possible values.

types modifers
``````````````
Each type can be associated with a number of modifiers, that will extend the number
of specification you describe for it:

values:
   a set of possible values that the attribute can take

name:
   the name of the attribute as displayed in the UI

default:
   The value the attribute takes if it is not defined explicitly

forbidden:
   a python expression checking whether this attribute should not be defined in
   a particular configuration

required:
   a python expression checking whether this attribute must be defined in
   a particular configuration

maybenull:
   a python expression checking whether this attribute must be defined in
   a particular configuration


More complex example
--------------------

The ``meta.yaml``:

.. code-block:: yaml

  root:
    type: dict
    kids:
       slaves:
          type: listofdicts
          name: Build Slaves
          kids:
            caps:
              type: dict
              name: Capabilities
              kids:
                  builder:
                      name: Used by builder
                      type: setofstrings
                      values: [ autolint, build ]
                      required: true
                  location:
                      type: location
                      required: true
                  speed:
                      type: string
                      default: fast
                      values: [fast,slow]
            slaves:
              type: setofstrings

matches a yaml file like:

.. code-block:: yaml

  slaves:
  -       caps:
                  builder: [build]
                  location: l4
          slaves: [buildbot1build]
  -       caps:
                  builder: [autolint, build]
                  location: l1
                  speed: fast
          slaves: [build3build, build4build, build5build]
