.. toctree::
   :hidden:

   ./register
   ./meta
   ./creators
   ./annotations

.. _features:

Features
========

There are four important parts that make up how ``strcs`` works:

* :ref:`The register <features_register_index>`
* :ref:`The meta object <features_meta_index>`
* :ref:`Creators <features_creators_index>`
* :ref:`Annotations <features_annotations_index>`

.. note:: It's a good idea to read about cattrs before reading about strcs,
   https://cattrs.readthedocs.io/en/latest/readme.html

.. _features_register_index:

The Register
------------

This object is where we centralise all the logic for turning one format of
information into another. Usually from a dictionary into an attrs class.

See :ref:`features_register`

.. _features_meta_index:

The Meta
--------

The Meta object stores values that may then be retrieved by deeply
nested objects. It has dictionary like set methods and special methods for
retrieving data based off type and name.

See :ref:`features_meta`

.. _features_creators_index:

Creators
--------

These are functions that take in one value and perform some action or transformation
before returning an instruction for how to make the desired object.

See :ref:`features_creators`

.. _features_annotations_index:

Annotations
-----------

It's possible to annotation the type on fields on a class to inject meta
information and/or replace the creator used for that field.

See :ref:`features_annotations`
