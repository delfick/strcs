Structures
==========

A Python3.10+ library that wraps `cattrs <https://cattrs.readthedocs.io>`_ for a
modular approach to constructing objects with the ability to string data through
the process.

Install from pypi::

    > python -m pip install strcs

Documentation at https://strcs.readthedocs.io/

Example
-------

.. code-block:: python

    import typing as tp

    import attrs

    import strcs

    reg = strcs.CreateRegister()
    creator = reg.make_decorator()

    Number = tp.NewType("Number", int)
    Word = tp.NewType("Word", str)


    @attrs.define(frozen=True)
    class Maths(strcs.MetaAnnotation):
        multiply: int

        def calculate(self, val: int) -> Number:
            return Number(val * self.multiply)


    class Thing:
        pass


    @attrs.define
    class Config:
        thing: tp.Annotated[Thing, strcs.FromMeta("thing")]
        words: list[Word]
        some_number: tp.Annotated[Number, Maths(multiply=2)]
        contrived1: str
        contrived2: str
        some_other_number: int = 16


    @creator(Number)
    def create_number(val: object, /, annotation: Maths) -> strcs.ConvertResponse[Number]:
        if not isinstance(val, int):
            return None

        return annotation.calculate(val)


    @creator(Word)
    def create_word(val: object, /, word_prefix: str = "") -> strcs.ConvertResponse[Word]:
        if not isinstance(val, str):
            return None

        return Word(f"{word_prefix}{val}")


    @creator(Config)
    def create_config(val: object, /) -> strcs.ConvertResponse[Config]:
        if not isinstance(val, dict):
            return None

        result = dict(val)
        if "contrived" in result:
            contrived = result.pop("contrived")
            result["contrived1"], result["contrived2"] = contrived.split("_")

        return result


    thing = Thing()
    meta = strcs.Meta({"thing": thing, "word_prefix": "the_prefix__"})

    config = reg.create(
        Config,
        {"words": ["one", "two"], "some_number": 20, "contrived": "stephen_bob"},
        meta=meta,
    )
    print(config)
    assert isinstance(config, Config)
    assert config.thing is thing
    assert config.words == ["the_prefix__one", "the_prefix__two"]
    assert config.some_number == 40
    assert config.some_other_number == 16
    assert config.contrived1 == "stephen"
    assert config.contrived2 == "bob"

Development
-----------

To have a virtualenv that has everything needed in it::
    
    > source run.sh activate

To run tests, linting, formatting, type checking::

    > ./test.sh
    > ./lint
    > ./format
    > ./types
