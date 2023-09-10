.. _features:

Features
========

There are five important parts that make up how ``strcs`` works:

.. note:: It's a good idea to read about cattrs before reading about strcs,
   https://cattrs.readthedocs.io/en/latest/readme.html

.. rubric:: The Register

This object is where we centralise all the logic for turning one format of
information into another. Usually from a dictionary into an attrs class.

See :ref:`features_register`

.. rubric:: The Meta

The Meta object stores values that may then be retrieved by deeply
nested objects. It has dictionary like set methods and special methods for
retrieving data based off type and name.

See :ref:`features_meta`

.. rubric:: Creators

These are functions that take in one value and perform some action or transformation
before returning an instruction for how to make the desired object.

See :ref:`features_creators`

.. rubric:: Annotations

It's possible to annotation the type on fields on a class to inject meta
information and/or replace the creator used for that field.

See :ref:`features_annotations`

.. rubric:: Disassembled

The ``strcs`` codebase has the ability to introspect and sort python type annotations so
that it can understand what is thrown at it. This functionality can also be used
without the rest of ``strcs`` functionality.

See :ref:`features_disassembled`
