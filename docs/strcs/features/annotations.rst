.. _features_annotations:

Annotations
===========

.. automodule:: strcs.annotations

.. code-block:: python

    import attrs
    import typing as tp
    import strcs

    reg = strcs.CreateRegister()
    creator = reg.make_decorator()


    @attrs.define(frozen=True)
    class MathsAnnotation(strcs.MergedMetaAnnotation):
        addition: int | None = None
        multiplication: int | None = None


    def do_maths(value: int, /, addition: int = 0, multiplication: int = 1) -> int:
        return (value + addition) * multiplication


    @attrs.define
    class Thing:
        val: tp.Annotated[int, strcs.Ann(MathsAnnotation(addition=20), do_maths)]


    @attrs.define
    class Holder:
        once: Thing
        twice: tp.Annotated[Thing, MathsAnnotation(multiplication=2)]
        thrice: tp.Annotated[Thing, MathsAnnotation(multiplication=3)]


    @creator(Thing)
    def create_thing(value: object) -> dict | None:
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
    assert attrs.asdict(holder) == {"once": {"val": 53}, "twice": {"val": 106}, "thrice": {"val": 159}}

.. note:: it is a good idea to set a default value when retrieving multiple values
   from meta that have the same type. In the example above ``addition`` and
   ``multiplication`` are both ints and to force ``strcs`` to match by name a
   default is specified. Otherwise if only addition or multiplication are in meta
   then they will both be set to the value of the one that is found.

.. autoclass:: strcs.Ann

.. autoclass:: strcs.FromMeta
