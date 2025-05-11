from typing import Annotated

import attrs

import strcs

reg = strcs.CreateRegister()
creator = reg.make_decorator()


@attrs.define(frozen=True)
class MultiplyAnnotation(strcs.MergedMetaAnnotation):
    multiply: int


@attrs.define
class Stuff:
    pass


@attrs.define
class SubOther:
    other: "Other"
    stuff: "Stuff"
    another: Annotated["Other", MultiplyAnnotation(multiply=2)]


@attrs.define
class Other:
    sub: SubOther | None
    val: int
    stuff: "Stuff"


@creator(Other)
def create_other(value: object, /, multiply: int = 1) -> dict | None:
    if isinstance(value, dict):
        return {"val": value["val"] * multiply, "sub": value["sub"]}

    if isinstance(value, int):
        return {
            "val": 0,
            "sub": {
                "other": {"val": value, "sub": None},
                "another": {"val": value, "sub": None},
            },
        }

    return None


class TestAutoResolvesTypesByDefault:
    def test_it_doesnt_work_until_we_resolve_types(self):
        other = reg.create(Other, 3)
        assert isinstance(other, Other)
        assert isinstance(other.stuff, Stuff)
        assert other.val == 0
        assert other.sub is not None
        assert isinstance(other.sub.stuff, Stuff)
        assert other.sub.other.val == 3
        assert other.sub.other.sub is None
        assert other.sub.another.val == 6
        assert other.sub.another.sub is None
