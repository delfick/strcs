# coding: spec

from attrs import define
import typing as tp
import strcs

reg = strcs.CreateRegister()
creator = reg.make_decorator()


@define(frozen=True)
class AdditionAnnotation(strcs.MergedAnnotation):
    addition: int


@define(frozen=True)
class MultiplicationAnnotation(strcs.MergedAnnotation):
    multiply_by: int


def change(val: float, /, addition: int = 0, multiply_by: int = 1) -> strcs.ConvertResponse:
    return float((val + addition) * multiply_by)


@define
class Thing:
    base: tp.Annotated[float, change]
    raised: tp.Annotated[float, strcs.Ann(AdditionAnnotation(addition=30), change)]
    elevated: tp.Annotated[float, strcs.Ann(AdditionAnnotation(addition=40), change)]


@define
class Things:
    once: Thing
    twice: tp.Annotated[Thing, MultiplicationAnnotation(multiply_by=2)]
    thrice: tp.Annotated[Thing, MultiplicationAnnotation(multiply_by=3)]


@creator(Thing)
def create_thing(val: float) -> strcs.ConvertResponse:
    return {"base": val, "raised": val + 0.1, "elevated": val + 0.2}


describe "modifying non attrs objects":

    it "is possible with annotations":
        things = reg.create(Things, {"once": 1.0, "twice": 2, "thrice": 3})
        assert isinstance(things, Things)

        assert things.once.base == 1
        assert things.once.raised == 31.1
        assert things.once.elevated == 41.2

        assert things.twice.base == 2 * 2
        assert things.twice.raised == 32.1 * 2
        assert things.twice.elevated == 42.2 * 2

        assert things.thrice.base == 3 * 3
        assert things.thrice.raised == 33.1 * 3
        assert things.thrice.elevated == 43.2 * 3
