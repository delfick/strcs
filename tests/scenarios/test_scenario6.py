import secrets
from typing import Annotated

import attrs

import strcs

reg = strcs.CreateRegister()
creator = reg.make_decorator()


@attrs.define
class Itself:
    one: int


@attrs.define
class Other:
    one: Itself
    two: Itself


@attrs.define
class Part:
    one: int
    identity: Annotated[str, strcs.FromMeta("identity")]


@attrs.define
class Thing:
    part1: Part
    part2: Part


@creator(Other)
def create_other(value: object, /, _register: strcs.CreateRegister) -> dict | None:
    if value is not strcs.NotSpecified:
        return None

    one = _register.create(Itself, 1)
    two = _register.create(Itself, 2)
    return {"one": one, "two": two}


@creator(Itself)
def create_itself(
    value: object, want: strcs.Type, /, _register: strcs.CreateRegister
) -> Itself | None:
    if not isinstance(value, int):
        return None

    return _register.create(want, {"one": value * 2})


@creator(Thing)
def create_thing(
    value: list[int], want: strcs.Type, /, _register: strcs.CreateRegister, _meta: strcs.Meta
) -> Thing:
    """Production quality would ensure value is indeed a list with two integers!!"""
    return _register.create(
        want,
        {"part1": {"one": value[0]}, "part2": {"one": value[1]}},
        meta=_meta.clone({"identity": secrets.token_hex(10)}),
    )


class TestCanCreateItselfWithAdditionalMeta:
    def test_it_works(self):
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


class TestCanCreatePartsWithoutAdditionalMeta:
    def test_it_works(self):
        other = reg.create(Other)
        assert isinstance(other, Other)
        assert other.one.one == 2
        assert other.two.one == 4


class TestCanCreateItselfWithoutAdditionalMeta:
    def test_it_works(self):
        itself = reg.create(Itself, 3)
        assert isinstance(itself, Itself)
        assert itself.one == 6
