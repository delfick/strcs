.. _features_disassembled:

Introspecting python types and their annotations
================================================

Within the ``strcs`` package are a bunch of code for understanding python
type annotations and class objects. These are used to introspect the types
that are provided when creating objects and those found on the fields
of classes.

The main entry point for these helpers is via :class:`strcs.Type` objects which
use the other helpers to normalise the complexities inherit in the way python
type annotations work at runtime.

This includes the ability to understand and extract from optionals and annotations,
the ability to understand type vars and how they work across inheritance, the
ability to order type annotations by complexity, and the ability to determine
the fields defined by a class.

Types
-----

.. autoclass:: strcs.Type
   :members:
   :member-order: bysource

.. autoclass:: strcs.TypeCache

.. autoclass:: strcs.MRO
    :members:

.. autoclass:: strcs.InstanceCheck
    :members:
    :undoc-members:

Extraction
----------

.. autoclass:: strcs.disassemble.IsAnnotated

.. autofunction:: strcs.disassemble.extract_optional

.. autofunction:: strcs.disassemble.extract_annotation

Fields
------

.. autoclass:: strcs.Field
    :members:

.. autofunction:: strcs.disassemble.fields_from_class

.. autofunction:: strcs.disassemble.fields_from_attrs

.. autofunction:: strcs.disassemble.fields_from_dataclasses

Scores
------

It is useful to be able to sort type annotations by complexity so that when
determining if a creator should be used for a particular type, more specific
creators are considered before less specific creators.

To achieve this, ``strcs`` has :class:`strcs.disassemble.Score` objects that are
returned from the ``score`` property on a :class:`strcs.Type` and are used when
sorting a sequence of :class:`strcs.Type` objects.

.. autoclass:: strcs.disassemble.Score
   :members:
   :member-order: bysource

.. autoclass:: strcs.disassemble.ScoreOrigin
   :members:
   :member-order: bysource
