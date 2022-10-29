.. _features_register:

The Register
============

The register is a central object that holds knowledge of how to transform data
into different types. It is used to get a decorator that is used to add those
:ref:`creators <features_creators>` and also used to then do a conversion:

.. code-block:: python

    import strcs

    reg = strcs.CreateRegister()
    creator = reg.make_decorator()

    # Then the creator may be used as a decorator to add knowledge about custom
    # transformations

    # Then objects may be created
    instance = reg.create(MyKls, some_data)

Multiple registers
------------------

It is easy to have multiple registers as the creator functions can ask for the
current register with the special ``_register: strcs.CreateRegister`` in the
signature:

.. code-block:: python

    from attrs import define
    import strcs

    reg = strcs.CreateRegister()
    creator = reg.make_decorator()


    @define
    class MyKls:
        one: int


    @creator(MyKls)
    def create_mykls(value: object, /, _register: strcs.CreateRegister) -> bool:
        assert _register is reg
        return True
    

    instance = reg.create(MyKls, {"one": 2})
    assert isinstance(instance, MyKls)

Resolving type annotations
--------------------------

There is a limitation whereby unresolved string type annotations will cause
errors as it won't know what object the string represents. strcs offers a helper
function based off ``typing.get_type_hints`` for resolving string type
annotations. It will automatically use this on any class (with special logic for
``attrs`` and ``dataclass`` classes) unless
``strcs.CreateRegister(auto_resolve_string_annotations=False)``.

A developer may manually do this resolution using ``strcs.resolve_types``:

.. code-block:: python

    from attrs import define
    import strcs


    class Stuff:
        one: int


    @define
    class Thing:
        stuff: "Stuff"
        other: "Other"


    @define
    class Other:
        thing: None | Thing


    strcs.resolve_types(Thing)

Note that if ``from __future__ import annotations`` is used then all types are
strings and require resolution. In that case if auto resolution on the register
is turned off then ``strcs.resolve_types`` may be used as a decorator in any
situation where types are already available at definition:

.. code-block:: python

    from __future__ import annotations
    from attrs import define
    import strcs


    @strcs.resolve_types
    class Stuff:
        one: int


    @define
    class Thing:
        stuff: "Stuff"
        other: "Other"


    @strcs.resolve_types
    @define
    class Other:
        thing: None | Thing


    strcs.resolve_types(Thing)

.. note:: Calling resolve_types will modify the fields on the class in place.
