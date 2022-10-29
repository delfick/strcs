.. _features_annotations:

Annotations
===========

Python has a ``typing.Annotated`` since Python 3.9 that lets the developer attach
information to a type and ``strcs`` will understand these annotations to get
an object it uses to modify the meta and/or creator:

.. code-block:: python

    from attrs import define, asdict
    import typing as tp
    import strcs

    reg = strcs.CreateRegister()
    creator = reg.make_decorator()


    @define(frozen=True)
    class MathsAnnotation(strcs.MergedAnnotation):
        addition: tp.Optional[int] = None
        multiplication: tp.Optional[int] = None


    def do_maths(value: int, /, addition: int = 0, multiplication: int = 1) -> int:
        return (value + addition) * multiplication


    @define
    class Thing:
        val: tp.Annotated[int, strcs.Ann(MathsAnnotation(addition=20), do_maths)]


    @define
    class Holder:
        once: Thing
        twice: tp.Annotated[Thing, MathsAnnotation(multiplication=2)]
        thrice: tp.Annotated[Thing, MathsAnnotation(multiplication=3)]


    @creator(Thing)
    def create_thing(value: object) -> None | dict:
        if not isinstance(value, int):
            return None
        return {"val": value}


    @creator(Holder)
    def create_holder(value: object) -> dict:
        if not isinstance(value, int):
            return None
        return {"once": value, "twice": value, "thrice": value}


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
        def create_mykls(value: object, /, annotation: MyAnnotation) -> None | dict:
            if not isinstance(value, str):
                return None
            return {"key": f"{value}-{annotation.one}-{annotation.two}"}

``strcs.MergedAnnotation``
    Will add the keys from the annotation into the meta. This would mean
    the above example becomes:

    .. code-block:: python

        @define(frozen=True)
        class MyAnnotation(strcs.MergedAnnotation):
            one: int
            two: int

        @creator(MyKls)
        def create_mykls(value: object, /, one: int = 0, two: int = 0) -> None | dict:
            if not isinstance(value, str):
                return None
            return {"key": f"{value}-{one}-{two}"}

    Optional keys are not added to meta if they are not set:

    .. code-block:: python

        @define(frozen=True)
        class MyAnnotation(strcs.MergedAnnotation):
            one: tp.Optional[int] = None
            two: tp.Optional[int] = None

        @creator(MyKls)
        def create_mykls(value: object, /, one: int = 0, two: int = 0) -> None | dict:
            if not isinstance(value, str):
                return None
            # one and two will be zero each instead of None when MyKls
            # is annotated with either of those not set respectively
            return {"key": f"{value}-{one}-{two}"}

Injecting data from meta
------------------------

Sometimes it is desirable to set a value straight from what is found in the Meta
object and this may be achieved via ``strcs.FromMeta``:

.. code-block:: python

    from attrs import define
    import typing as tp
    import strcs

    reg = strcs.CreateRegister()
    creator = reg.make_decorator()


    class Magic:
        def incantation(self) -> str:
            return "abracadabra!"


    @define
    class Wizard:
        magic: tp.Annotated[Magic, strcs.FromMeta("magic")]


    wizard = reg.create(Wizard, meta=strcs.Meta({"magic": Magic()}))
    assert wizard.magic.incantation() == "abracadabra!"
