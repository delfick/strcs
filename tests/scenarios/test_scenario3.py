import typing as tp

import attrs

import strcs

reg = strcs.CreateRegister()
creator = reg.make_decorator()


@attrs.define(frozen=True)
class AdditionAnnotation(strcs.MergedMetaAnnotation):
    addition: int


@attrs.define(frozen=True)
class MultiplicationAnnotation(strcs.MergedMetaAnnotation):
    multiply_by: int


def change(value: object, /, addition: int = 0, multiply_by: int = 1) -> float | None:
    if not isinstance(value, (float, int)):
        return None
    return float((value + addition) * multiply_by)


@attrs.define
class Thing:
    base: tp.Annotated[float, change]
    raised: tp.Annotated[float, strcs.Ann(AdditionAnnotation(addition=30), change)]
    elevated: tp.Annotated[float, strcs.Ann(AdditionAnnotation(addition=40), change)]


@attrs.define
class Things:
    once: Thing
    twice: tp.Annotated[Thing, MultiplicationAnnotation(multiply_by=2)]
    thrice: tp.Annotated[Thing, MultiplicationAnnotation(multiply_by=3)]


@creator(Thing)
def create_thing(value: object, /) -> dict | None:
    if not isinstance(value, (int, float)):
        return None
    return {"base": value, "raised": value + 0.1, "elevated": value + 0.2}


class TestModifyingNonAttrsObjects:
    def test_it_is_possible_with_annotations(self):
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
