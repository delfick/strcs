# coding: spec

from attrs import define
import typing as tp
import pytest
import strcs


reg = strcs.CreateRegister(auto_resolve_string_annotations=False)
creator = reg.make_decorator()


@define(frozen=True)
class MultiplyAnnotation(strcs.MergedAnnotation):
    multiply: int


@define
class SubOther:
    other: "Other"
    another: tp.Annotated["Other", MultiplyAnnotation(multiply=2)]


@define
class Other:
    sub: SubOther | None
    val: int


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


describe "Fails to create if the types are strings":

    it "doesn't work until we resolve types":
        with pytest.raises(
            strcs.errors.UnableToConvert,
            match="Unsupported type: 'Other'. Register a structure hook for it.+",
        ):
            reg.create(Other, 3)

        strcs.resolve_types(SubOther)

        other = reg.create(Other, 3)
        assert isinstance(other, Other)
        assert other.val == 0
        assert other.sub is not None
        assert other.sub.other.val == 3
        assert other.sub.other.sub is None
        assert other.sub.another.val == 6
        assert other.sub.another.sub is None
