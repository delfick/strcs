# coding: spec

from attrs import define, asdict
from functools import partial
import typing as tp
import strcs

reg = strcs.CreateRegister()
creator = partial(strcs.CreatorDecorator, reg)


@define(frozen=True)
class NumberAnnotation(strcs.Annotation):
    add: int


@define
class Number:
    val: int


@define
class Overall:
    one: tp.Annotated[Number, NumberAnnotation(add=12)]
    two: tp.Annotated[Number, NumberAnnotation(add=10)]


@creator(Number)
def create_number(
    val: int | tp.Type[strcs.NotSpecified], /, ann: NumberAnnotation
) -> strcs.ConvertResponse:
    if val is strcs.NotSpecified:
        val = 0
    return {"val": val + ann.add}


describe "Scenario 2":

    it "can get annotated information from class definition":
        overall = reg.create(Overall, {"two": 20})
        assert asdict(overall) == {"one": {"val": 12}, "two": {"val": 30}}

        overall = reg.create(Overall, {"one": 1, "two": 4})
        assert asdict(overall) == {"one": {"val": 13}, "two": {"val": 14}}
