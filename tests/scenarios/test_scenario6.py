# coding: spec

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
) -> Thing:
    """Production quality would ensure val is indeed a list with two integers!!"""
    return _register.create(
        want,
        {"part1": {"one": val[0]}, "part2": {"one": val[1]}},
        meta=_meta.clone({"identity": secrets.token_hex(10)}),
        recursed=True,
    )


describe "can create itself with additional meta":

    it "works":
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
