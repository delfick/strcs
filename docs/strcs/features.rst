.. _features:

Features
========

There are four important parts that make up how ``strcs`` works:

* :ref:`The register <features_register>`
* :ref:`The meta object <features_meta>`
* :ref:`Creators <features_creators>`
* :ref:`Annotations <features_annotations>`

.. note:: It's a good idea to read about cattrs before reading about strcs,
   https://cattrs.readthedocs.io/en/latest/readme.html

.. _features_register:

The Register
------------

This object is where we centralise all the logic for turning one format of
information into another. Usually from a dictionary into an attrs class.

It and the decorator we use to add to it, are created with the following:

.. code-block:: python

    from functools import partial
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

The Meta object stores values that may then be retrieved by deeply
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

.. note: The retrieve_one method also takes zero or more patterns

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

.. _features_creators:

Creators
--------

These are functions that take in one value and perform some action or transformation
before returning an instruction for how to make the desired object.

For example:

.. code-block:: python

    from functools import partial
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

``strcs`` allows creators to be one of the following forms:

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

There are also three special names that allow getting the meta object, the cattrs
converter being used, and the register being used:

.. code-block:: python

    from functools import partial
    from attrs import define
    import cattrs
    import strcs

    reg = strcs.CreateRegister()
    creator = partial(strcs.CreatorDecorator, reg)

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
++++++++++++++++++++++++

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
+++++++++++++++++++++++++++++++

It is possible to use the register to create the type your creator is using but
with different meta information. The trick is to make sure ``recursed=True`` is
set when ``_register.create`` is called so that ``strcs`` doesn't enter an
infinite loop:

.. code-block:: python

    from functools import partial
    from attrs import define
    import typing as tp
    import secrets
    import strcs


    reg = strcs.CreateRegister()
    creator = partial(strcs.CreatorDecorator, reg)


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
++++++++++++++++++

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

    from functools import partial
    from attrs import define
    import strcs

    reg = strcs.CreateRegister()
    creator = partial(strcs.CreatorDecorator, reg)


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

    from functools import partial
    from attrs import define
    import typing as tp
    import strcs

    reg = strcs.CreateRegister()
    creator = partial(strcs.CreatorDecorator, reg)


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

.. _features_annotations:

Annotations
-----------

It's possible to annotation the type on fields on a class to inject meta
information and/or replace the creator used for that field.

Python has a ``typing.Annotated`` since Python 3.9 that lets the developer attach
information to a type and ``strcs`` will understand these annotations to get
an object it uses to modify the meta and/or creator:

.. code-block:: python

    from attrs import define, asdict
    from functools import partial
    import typing as tp
    import strcs

    reg = strcs.CreateRegister()
    creator = partial(strcs.CreatorDecorator, reg)


    @define(frozen=True)
    class MathsAnnotation(strcs.MergedAnnotation):
        addition: tp.Optional[int] = None
        multiplication: tp.Optional[int] = None


    def do_maths(val: int, /, addition: int = 0, multiplication: int = 1) -> int:
        return (val + addition) * multiplication


    @define
    class Thing:
        val: tp.Annotated[int, strcs.Ann(MathsAnnotation(addition=20), do_maths)]


    @define
    class Holder:
        once: Thing
        twice: tp.Annotated[Thing, MathsAnnotation(multiplication=2)]
        thrice: tp.Annotated[Thing, MathsAnnotation(multiplication=3)]


    @creator(Thing)
    def create_thing(val: int) -> strcs.ConvertResponse:
        return {"val": val}


    @creator(Holder)
    def create_holder(val: int) -> strcs.ConvertResponse:
        return {"once": val, "twice": val, "thrice": val}


    holder = reg.create(Holder, 33)
    assert isinstance(holder, Holder)
    assert asdict(holder) == {"once": {"val": 53}, "twice": {"val": 106}, "thrice": {"val": 159}}

.. note:: it is a good idea to set a default value when retrieving multiple values
   from meta that have the same type. In the example above ``addition`` and
   ``multiplication`` are both ints and to force ``strcs`` to match by name a
   default is specified. Otherwise if only addition or multiplication are in meta
   then they will both be set to the value of the one that is found.

An annotation may either be an instance of ``strcs.Ann``, an instance of
``strcs.Annotation`` or a callable object. When a value is supplied that isn't
``strcs.Ann`` then one is created from that value.

So if an ``strcs.Annotation`` is provided then it will create
``strcs.Ann(meta=found)``, otherwise if the value is a callable then
``strcs.Ann(creator=found)``.

``strcs`` will use the ``adjusted_meta`` and ``adjusted_creator`` on the ``Ann``
object to find a new meta or new creator to use for that field.

New Meta will persist for any transformation that occurs below that field, but
a new creator will only be used for that field.

When providing a meta object to ``Ann``, there are two default strategies to
choose from: ``strcs.Annotation`` and ``strcs.MergedAnnotation``. A custom
strategy may be provided by implementing ``adjusted_meta`` on the ``Annotation``.

``strcs.Annotation``
    Will return a cloned meta containing ``__call_defined_annotation__`` so that
    the creator may retrieve the entire ``Annotation`` using the type of that
    annotation.

    For example:

    .. code-block:: python

        @define(frozen=True)
        class MyAnnotation(strcs.Annotation):
            one: int
            two: int

        @creator(MyKls)
        def create_mykls(val: str, /, annotation: MyAnnotation) -> strcs.ConvertResponse:
            return {"key": f"{val}-{annotation.one}-{annotation.two}"}

``strcs.MergedAnnotation``
    Will add the keys from the annotation into the meta. This would mean
    the above example becomes:

    .. code-block:: python

        @define(frozen=True)
        class MyAnnotation(strcs.MergedAnnotation):
            one: int
            two: int

        @creator(MyKls)
        def create_mykls(val: str, /, one: int = 0, two: int = 0) -> strcs.ConvertResponse:
            return {"key": f"{val}-{one}-{two}"}

    Optional keys are not added to meta if they are not set:

    .. code-block:: python

        @define(frozen=True)
        class MyAnnotation(strcs.MergedAnnotation):
            one: tp.Optional[int] = None
            two: tp.Optional[int] = None

        @creator(MyKls)
        def create_mykls(val: str, /, one: int = 0, two: int = 0) -> strcs.ConvertResponse:
            # one and two will be zero each instead of None when MyKls
            # is annotated with either of those not set respectively
            return {"key": f"{val}-{one}-{two}"}

Injecting data from meta
++++++++++++++++++++++++

Sometimes it is desirable to set a value straight from what is found in the Meta
object and this may be achieved via ``strcs.FromMeta``:

.. code-block:: python

    from functools import partial
    from attrs import define
    import typing as tp
    import strcs

    reg = strcs.CreateRegister()
    creator = partial(strcs.CreatorDecorator, reg)


    class Magic:
        def incantation(self) -> str:
            return "abracadabra!"


    @define
    class Wizard:
        magic: tp.Annotated[Magic, strcs.FromMeta("magic")]


    wizard = reg.create(Wizard, meta=strcs.Meta({"magic": Magic()}))
    assert wizard.magic.incantation() == "abracadabra!"
