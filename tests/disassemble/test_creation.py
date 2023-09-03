# coding: spec
import typing as tp

import attrs
import cattrs
import pytest

import strcs
from strcs.disassemble.creation import fill, instantiate


@pytest.fixture()
def type_cache() -> strcs.TypeCache:
    return strcs.TypeCache()


describe "fill":
    it "turns NotSpecified into an empty dictionary", type_cache: strcs.TypeCache:

        class Thing:
            pass

        want = strcs.Type.create(Thing, expect=object, cache=type_cache)

        assert fill(want, strcs.NotSpecified) == {}

    it "complains if res is not a mapping", type_cache: strcs.TypeCache:

        class Thing:
            pass

        want = strcs.Type.create(Thing, expect=object, cache=type_cache)

        for res in (1, 0, True, False, [], [1], set(), lambda: 1, Thing, Thing()):
            with pytest.raises(ValueError, match="Can only fill mappings"):
                fill(want, res)

    it "fills in annotated or other objects with NotSpecified", type_cache: strcs.TypeCache:

        class Two:
            pass

        @attrs.define
        class Thing:
            one: tp.Annotated[int, 1]
            two: Two
            three: bool
            four: int

        res = {"four": 1}
        want = strcs.Type.create(Thing, expect=object, cache=type_cache)
        assert fill(want, res) == {"one": strcs.NotSpecified, "two": strcs.NotSpecified, "four": 1}

    it "doesn't override fields", type_cache: strcs.TypeCache:

        class Two:
            pass

        @attrs.define
        class Thing:
            one: tp.Annotated[int, 1]
            two: Two
            three: bool
            four: int

        two = Two()
        res = {"one": 3, "two": two, "three": True, "four": 1}
        want = strcs.Type.create(Thing, expect=object, cache=type_cache)
        assert fill(want, res) == {"one": 3, "two": two, "three": True, "four": 1}

describe "instantiate":
    it "returns None if the result is optional and res is None", type_cache: strcs.TypeCache:

        class Thing:
            pass

        want = strcs.Type.create(Thing | None, expect=object, cache=type_cache)
        assert instantiate(want, None, cattrs.Converter()) is None

    it "returns None if want None and are None", type_cache: strcs.TypeCache:
        want = strcs.Type.create(None, expect=object, cache=type_cache)
        assert instantiate(want, None, cattrs.Converter()) is None

    it "complains if res is None and we aren't optional or None", type_cache: strcs.TypeCache:

        class Thing:
            pass

        want = strcs.Type.create(Thing, expect=object, cache=type_cache)
        with pytest.raises(ValueError, match="Can't instantiate object with None"):
            instantiate(want, None, cattrs.Converter())

describe "creation":
    it "deals with private fields in an attrs class":
        reg = strcs.CreateRegister()

        @attrs.define
        class Thing:
            one: int
            _two: int

        thing = Thing(one=1, two=20)
        assert thing.one == 1
        assert thing._two == 20

        thing2 = reg.create(Thing, {"one": 1, "two": 20})
        assert thing2.one == 1
        assert thing2._two == 20

    it "deals with private fields in not attrs class":
        reg = strcs.CreateRegister()

        class Thing:
            def __init__(self, one: int, _two: int):
                self.one = one
                self._two = _two

        thing = Thing(one=1, _two=20)
        assert thing.one == 1
        assert thing._two == 20

        thing2 = reg.create(Thing, {"one": 1, "_two": 20})
        assert thing2.one == 1
        assert thing2._two == 20

    it "invokes creators for annotated fields":
        reg = strcs.CreateRegister()

        def doubler(val: object, /) -> int:
            assert isinstance(val, int)
            return val * 2

        class Thing:
            def __init__(self, one: tp.Annotated[int, strcs.Ann(creator=doubler)]):
                self.one = one

        thing = Thing(one=1)
        assert thing.one == 1

        thing2 = reg.create(Thing, {"one": 1})
        assert thing2.one == 2

    it "invokes creators for annotated fields even if not provided":
        reg = strcs.CreateRegister()

        def doubler(val: object, /) -> int:
            assert val is strcs.NotSpecified
            return 200

        class Thing:
            def __init__(self, one: tp.Annotated[int, strcs.Ann(creator=doubler)]):
                self.one = one

        with pytest.raises(TypeError):
            Thing()  # type: ignore[call-arg]

        thing2 = reg.create(Thing)
        assert thing2.one == 200

    it "invokes creators for other classes even if not provided":
        reg = strcs.CreateRegister()

        @attrs.define
        class Two:
            three: bool = True

        class Thing:
            def __init__(self, two: Two):
                self.two = two

        with pytest.raises(TypeError):
            Thing()  # type: ignore[call-arg]

        thing2 = reg.create(Thing)
        assert thing2.two == Two(three=True)

    it "doesn't care for fields on parents not part of the child", type_cache: strcs.TypeCache:
        reg = strcs.CreateRegister()

        class One:
            def __init__(self, one: int, two: int):
                self.one = one
                self.two = two

        class Two(One):
            def __init__(self, two: int, three: int):
                super().__init__(one=2, two=two)
                self.three = three

        want = strcs.Type.create(Two, expect=object, cache=type_cache)

        assert want.fields == [
            strcs.Field(
                name="one",
                disassembled_type=strcs.Type.create(int, cache=type_cache),
                owner=One,
                original_owner=One,
            ),
            strcs.Field(
                name="two",
                disassembled_type=strcs.Type.create(int, cache=type_cache),
                owner=Two,
                original_owner=One,
            ),
            strcs.Field(
                name="three",
                disassembled_type=strcs.Type.create(int, cache=type_cache),
                owner=Two,
                original_owner=Two,
            ),
        ]

        thing = Two(two=3, three=4)
        assert thing.one == 2
        assert thing.two == 3
        assert thing.three == 4

        thing2 = reg.create(Two, {"two": 3, "three": 4})
        assert thing2.one == 2
        assert thing2.two == 3
        assert thing2.three == 4

        thing3 = reg.create(Two, {"one": 20, "two": 3, "three": 4})
        assert thing3.one == 2
        assert thing3.two == 3
        assert thing3.three == 4
