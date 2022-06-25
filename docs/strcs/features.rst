.. _features:

Features
========

There are four important parts that make up how ``strcs`` works:

* :ref:`The register <features_register>`
* :ref:`The meta object <features_meta>`
* :ref:`Creators <features_creators>`
* :ref:`Annotations <features_annotations>`

.. _features_register

The Register
------------

This object is where we centralise all the logic for turning one format of
information into another. Usually from a dictionary into an attrs class.

It and the decorator we use to add to it, are created with the following:

.. code-block:: python

    import strcs

    reg = strcs.CreateRegister()
    creator = partial(strcs.CreatorDecorator, reg)

.. note:: it is possible to have multiple registers and it is possible to
   ask for the current register when inside a creator function.

:ref:`Creators <features_creators>` are added to the register as functions or
generators that take in some value and return something that ``strcs`` will then
use to create (or have) the final object.

.. _features_meta

The Meta
--------

The Meta object lets you store values that can then be retrieved by deeply
nested objects. It has dictionary like set methods and special methods for
retrieving data based off type and name:

.. code-block:: python

    import strcs

    meta = strcs.Meta()
    meta["one"] = 1
    meta["two"] = "2"
    meta.update({"three": 3, "four": True})
    assert meta.data == {"one": 1, "two": "2", "three": 3, "four": True}

    assert meta.find_by_type(int) == {"one": 1, "three": 3}
    assert meta.find_by_type(str) == {"two": "2"}
    assert meta.retrieve_one(int, "three") == 3
    assert meta.retrieve_one(int, "one") == 1

The meta contains a cattrs converter that will be used for much of the heavy
lifting. https://cattrs.readthedocs.io/en/latest/converters.html. You may use
this to provide a custom converter with extra structure and unstructure hooks
you may require.

You may also clone a meta and provide a different converter, extra information,
or completely different information:

.. code-block:: python

    import cattrs
    import strcs

    meta1 = strcs.Meta({"one": 1})
    meta2 = meta1.clone({"two": 2})
    meta3 = meta1.clone(data_override={"three": 3})

    new_converter = cattrs.Converter()
    meta4 = meta1.clone(converter=new_converter)

    assert meta1.data == {"one": 1}
    assert meta2.data == {"one": 1, "two": 2}

    assert meta3.data == {"three": 3}
    assert meta4.converter is not meta3.converter
    assert meta3.converter is meta2.converter

Finally, the ability to retrieve information from a meta can be based on deeply
nested patterns.

.. note: The retrieve_one method also takes zero or more patterns

For example:

.. code-block:: python

    import strcs

    meta = strcs.Meta({"a": {"b": {"d": 4, "e": 5}}, "a.b": {"f": 6}, "a.bc": True})

    # Note that using object as a type is considered a wildcard
    # You may provide more specific types to match against
    assert meta.retrieve_patterns(object, "a.b") == {"a.b": {"f": 6}}
    assert meta.retrieve_patterns(int, "a.b.d", "a.b.e") == {"a.b.d": 4, "a.b.e": 5}
    assert meta.retrieve_patterns(object , "a.b.*") == {"a.b.d": 4, "a.b.e": 5, "a.b.f": 6}
    assert meta.retrieve_patterns(object, "a.b*") == {"a.b": {"f": 6}, "a.bc": True}

.. _features_creators

Creators
--------

.. _features_annotations

Annotations
-----------
