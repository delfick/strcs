.. _features_meta:

Meta
====

The Meta object stores values that may then be retrieved by deeply
nested objects. It has dictionary like set methods and special methods for
retrieving data based off type and name.

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

The meta contains a cattrs converter that is used for much of the heavy
lifting. https://cattrs.readthedocs.io/en/latest/converters.html. This may be
used to provide a custom converter with extra structure and unstructure hooks
that may be required.

A Meta object may also be cloned to provide a different converter, extra
information, or completely different information:

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

Finally, the ability to retrieve information from a meta may also be based on
deeply nested patterns.

.. note:: The retrieve_one method also takes zero or more patterns

For example:

.. code-block:: python

    import strcs

    meta = strcs.Meta({"a": {"b": {"d": 4, "e": 5}}, "a.b": {"f": 6}, "a.bc": True})

    # Note that using object as a type is considered a wildcard
    # More specific types to match against may also be provided
    assert meta.retrieve_patterns(object, "a.b") == {"a.b": {"f": 6}}
    assert meta.retrieve_patterns(int, "a.b.d", "a.b.e") == {"a.b.d": 4, "a.b.e": 5}
    assert meta.retrieve_patterns(object , "a.b.*") == {"a.b.d": 4, "a.b.e": 5, "a.b.f": 6}
    assert meta.retrieve_patterns(object, "a.b*") == {"a.b": {"f": 6}, "a.bc": True}

