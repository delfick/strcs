# coding: spec

from attrs import define
import typing as tp
import strcs


reg = strcs.CreateRegister()
creator = reg.make_decorator()


@define(frozen=True)
class MultiplyAnnotation(strcs.MergedAnnotation):
    multiply: int


@define
class Stuff:
    pass


@define
class SubOther:
    other: "Other"
    stuff: "Stuff"
    another: tp.Annotated["Other", MultiplyAnnotation(multiply=2)]


@define
class Other:
    sub: None | SubOther
    val: int
    stuff: "Stuff"


@creator(Other)
def create_other(val: object, /, multiply: int = 1) -> None | dict:
    if isinstance(val, dict):
        return {"val": val["val"] * multiply, "sub": val["sub"]}

    if isinstance(val, int):
        return {
            "val": 0,
            "sub": {
                "other": {"val": val, "sub": None},
                "another": {"val": val, "sub": None},
            },
        }

    return None


describe "Auto resolves types by default":

    it "doesn't work until we resolve types":
        other = reg.create(Other, 3)
        assert isinstance(other, Other)
        assert isinstance(other.stuff, Stuff)
        assert other.val == 0
        assert isinstance(other.sub.stuff, Stuff)
        assert other.sub.other.val == 3
        assert other.sub.other.sub is None
        assert other.sub.another.val == 6
        assert other.sub.another.sub is None
