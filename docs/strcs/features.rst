.. _features:

Features
========

There are four important parts that make up how ``strcs`` works:

* :ref:`The register <features_register>`
* :ref:`The meta object <features_meta>`
* :ref:`Creators <features_creators>`
* :ref:`Annotations <features_annotations>`

.. _features_register:

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

.. _features_meta:

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

.. _features_creators:

Creators
--------

These are functions that take in one value and perform some action or transformation
before returning an instruction for how to make the desired object.

For example:

.. code-block:: python

    from attrs import define
    import strcs

    reg = strcs.CreateRegister()
    creator = partial(strcs.CreatorDecorator, reg)

    @define
    class Thing:
        one: int

    @creator(Thing)
    def create_thing(val: int, /) -> strcs.ConvertResponse:
        return {"one": val}

    thing = reg.create(Thing, 23)
    assert isinstance(thing, Thing)
    assert thing.one == 23

Here the ``create_thing`` creator that has been registered for the ``Thing``
class will convert an integer into an instance of the ``Thing`` class. It does
this by returning a dictionary that cattrs will then use to create the instance.

.. note:: the type annotation on ``val`` in the creator is not enforced and
   should only be considered as documentation. It is up to the creator to
   understand the shape of that variable.

Creators can take one of the following forms:

.. code-block:: python

   import typing as tp
   import strcs


   @creator(T)
   def creator() -> strcs.ConvertResponse:
       ...


   @creator(T)
   def creator(val: tp.Any) -> strcs.ConvertResponse:
       ...


   @creator(T)
   def creator(val: tp.Any, want: tp.Type[T], /) -> strcs.ConvertResponse:
       ...


   # if there are more than one argument and the slash doesn't say they are
   # positional, then they are interpreted as found from the meta object
   @creator(T)
   def creator(meta_arg: U, meta_arg2: Z, ...) -> strcs.ConvertResponse:
       ...


   @creator(T)
   def creator(val: tp.Any, /, meta_arg: U, meta_arg2: Z, ...) -> strcs.ConvertResponse:
       ...


   @creator(T)
   def creator(val: tp.Any, want: tp.Type[T], /, meta_arg: U, meta_arg2: Z, ...) -> strcs.ConvertResponse:
       ...

.. note:: The slash is a feature new to python since python3.8 and let us say
   any arguments before the slash are positional only, which means those names
   do not conflict with any names used in keyword arguments. For more
   information see https://realpython.com/lessons/positional-only-arguments/

A creator gets the ``val`` that needs to be transformed, the type that we ``want``
to create (note this may be a subclass of the type used in the decorator) and
any arguments from meta.

There are also three special names that can get us the meta object, the cattrs
converter being used, and the register being used:

.. code-block:: python

    from functools import partial
    from attrs import define
    import cattrs
    import strcs

    reg = strcs.CreateRegister()
    creator = partial(strcs.CreatorDecorator, reg)

    # You don't have to create them yourselves if you're not adding anything
    # to them, but I'm doing so here for demonstration
    converter = cattrs.Converter()
    meta = strcs.Meta(converter=converter)


    @define
    class Thing:
        one: int


    @creator(Thing)
    def create_thing(
        val: dict, /, _meta: strcs.Meta, _converter: cattrs.Converter, _register: strcs.CreateRegister
    ) -> strcs.ConvertResponse:
        assert _meta is meta
        assert _converter is converter
        assert _register is reg
        return val


    thing = reg.create(Thing, {"one": 32}, meta=meta)
    assert isinstance(thing, Thing)
    assert thing.one == 32

.. note:: for those special arguments to work they must have the correct name
   and type annotation!

   ``_meta: strcs.Meta`` Gives you the meta object

   ``_converter: cattrs.Converter`` Gives you the current converter

   ``_register: strcs.CreateRegister`` Gives you the current register

.. _features_annotations:

Annotations
-----------
