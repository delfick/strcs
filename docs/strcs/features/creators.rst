.. _features_creators:

Creators
========

These are functions and generators that take in one value and perform some
action or transformation before returning an instruction for how to make the
desired object.

For example:

.. code-block:: python

    from attrs import define
    import strcs

    reg = strcs.CreateRegister()
    creator = reg.make_decorator()


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

``strcs`` allows creators to be one of the following forms:

.. code-block:: python

   import typing as tp
   import strcs


   @creator(T)
   def creator() -> strcs.ConvertResponse:
       """Useful for static values"""
       ...


   @creator(T)
   def creator(val: tp.Any, /) -> strcs.ConvertResponse:
       """
       Sometimes all we need is the value to be transformed

       Note the slash is important!
       """
       ...


   @creator(T)
   def creator(val: tp.Any, want: tp.Type[T], /) -> strcs.ConvertResponse:
       """
       The type being created may be a subclass of T and want will be that type

       It also means if we do need to reference the type, we don't need to couple
       the body of the function to the type it is registered to.
       """
       ...


   # if there are more than one argument and the slash doesn't say they are
   # positional, then they are interpreted as found from the meta object
   @creator(T)
   def creator(meta_arg: U, meta_arg2: Z, ...) -> strcs.ConvertResponse:
       ...


   @creator(T)
   def creator(val: tp.Any, /, meta_arg: U, meta_arg2: Z, ...) -> strcs.ConvertResponse:
       """Meta arguments are found by name then type"""
       ...


   @creator(T)
   def creator(val: tp.Any, want: tp.Type[T], /, meta_arg: U, meta_arg2: Z, ...) -> strcs.ConvertResponse:
       """
       The positional only slash means that val and want aren't taken from
       possible names from the meta
       """
       ...

.. note:: The slash is a feature new to python since python3.8 and let us say
   any arguments before the slash are positional only, which means those names
   do not conflict with any names used in keyword arguments. For more
   information see https://realpython.com/lessons/positional-only-arguments/

A creator gets the ``val`` that needs to be transformed, the type that we ``want``
to create (note this may be a subclass of the type used in the decorator) and
any arguments from meta.

There are also three special names that allow getting the meta object, the cattrs
converter being used, and the register being used:

.. code-block:: python

    from attrs import define
    import cattrs
    import strcs

    reg = strcs.CreateRegister()
    creator = reg.make_decorator()

    # These don't need to be created if nothing is done with them
    # This example does so for demonstration below
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

   ``_meta: strcs.Meta`` Provides the meta object

   ``_converter: cattrs.Converter`` Provides the current converter

   ``_register: strcs.CreateRegister`` Provides the current register

Returning from a creator
------------------------

A creator must return a ``strcs.ConvertResponse`` which is either ``None``,
``True``, a dictionary, or an instance of the class we are creating.

Returning None
    This means the value could not be transformed and will result in ``strcs``
    raising an error

Returning True
    Will make ``strcs`` use the val as is

Returning a dictionary
    Will make ``strcs`` use ``converter.structure_attrs_fromdict`` on that
    dictionary to make the object we are creating.

Returning an instance
    ``strcs`` will assume if the result is already an instance of the object
    that it should use it as is.

Using register inside a creator
-------------------------------

It is possible to use the register to create the type your creator is using but
with different meta information. The trick is to make sure ``recursed=True`` is
set when ``_register.create`` is called so that ``strcs`` doesn't enter an
infinite loop:

.. code-block:: python

    from attrs import define
    import typing as tp
    import secrets
    import strcs


    reg = strcs.CreateRegister()
    creator = reg.make_decorator()


    @define
    class Part:
        one: int
        identity: tp.Annotated[str, strcs.FromMeta("identity")]


    @define
    class Thing:
        part1: Part
        part2: Part


    @creator(Thing)
    def create_thing(
        val: list[int], want: tp.Type, /, _register: strcs.CreateRegister, _meta: strcs.Meta
    ) -> strcs.ConvertResponse:
        """Production quality would ensure val is indeed a list with two integers!!"""
        return _register.create(
            want,
            {"part1": {"one": val[0]}, "part2": {"one": val[1]}},
            meta=_meta.clone({"identity": secrets.token_hex(10)}),
            recursed=True,
        )


    thing1 = reg.create(Thing, [1, 2])
    assert isinstance(thing1, Thing)
    assert thing1.part1.one == 1
    assert len(thing1.part1.identity) == 20
    assert thing1.part2.one == 2
    assert len(thing1.part2.identity) == 20
    assert thing1.part1.identity == thing1.part2.identity

    thing2 = reg.create(Thing, [2, 3])
    assert isinstance(thing2, Thing)
    assert thing2.part1.one == 2
    assert len(thing2.part1.identity) == 20
    assert thing2.part2.one == 3
    assert len(thing2.part2.identity) == 20
    assert thing2.part1.identity == thing2.part2.identity

    assert thing1.part1.identity != thing2.part1.identity

Generator creators
------------------

Creators may also be generator functions that yield zero, once, or twice. If the
generator doesn't yield at all, then ``strcs`` will raise an exception to say
the input data couldn't be transformed.

On the first yield, ``strcs`` will use the yield value as it would in a normal
creator and provide access to the resulting object. The generator may then
do what it wants with that object. A second yield will instruct ``strcs`` to use
this second yielded object as the result, otherwise it will use the object it
created from the first yield.

For example:

.. code-block:: python

    from attrs import define
    import strcs

    reg = strcs.CreateRegister()
    creator = reg.make_decorator()


    @define
    class Thing:
        one: int

        def do_something(self):
            print(f"DOING SOMETHING WITH {self.one}")


    @creator(Thing)
    def create_thing(val: int):
        res = yield {"one": val}
        assert isinstance(res, Thing)
        assert res.one == val

        res.do_something()
        # We don't yield again, so res is the value that is used


    thing = reg.create(Thing, 23)
    # prints "DOING SOMETHING WITH 23" to the console
    assert isinstance(thing, Thing)
    assert thing.one == 23

Generator creators may also yield other generators:

.. code-block:: python

    from attrs import define
    import typing as tp
    import strcs

    reg = strcs.CreateRegister()
    creator = reg.make_decorator()


    called = []


    @define
    class Thing:
        one: int = 1

        def __post_attrs_init__(self):
            self.two = None
            self.three = None


    def recursion_is_fun(value: tp.Any):
        assert isinstance(value, dict)
        assert value == {"one": 20}
        called.append(2)
        made = yield {"one": 60}
        made.two = 500
        called.append(3)


    @creator(Thing)
    def make(value: tp.Any):
        called.append(1)
        made = yield recursion_is_fun(value)
        made.three = 222
        called.append(4)


    made = reg.create(Thing, {"one": 20})
    assert isinstance(made, Thing)
    assert made.one == 60
    assert made.two == 500
    assert made.three == 222
    assert called == [1, 2, 3, 4]

Async creators
--------------

It's not possible to have async creators because as of 2022, ``cattrs`` itself
does not support async enabled hooks.
