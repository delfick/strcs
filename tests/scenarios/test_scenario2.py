# coding: spec

from attrs import define, asdict
import typing as tp
import strcs

reg = strcs.CreateRegister()
creator = reg.make_decorator()


@define(frozen=True)
class NumberAnnotation(strcs.Annotation):
    add: int


@define(frozen=True)
class SentenceAnnotation(strcs.MergedAnnotation):
    prefix: str


@define
class Number:
    val: int


@define
class Sentence:
    val: str


@define
class Overall:
    one: tp.Annotated[Number, NumberAnnotation(add=12)]
    two: tp.Annotated[Number, NumberAnnotation(add=10)]

    three: tp.Annotated[Sentence, SentenceAnnotation(prefix="stuff")]
    four: Sentence


@creator(Number)
def create_number(
    val: int | tp.Type[strcs.NotSpecified], /, ann: NumberAnnotation
) -> strcs.ConvertResponse:
    if val is strcs.NotSpecified:
        val = 0
    return {"val": val + ann.add}


@creator(Sentence)
def create_sentence(
    val: str | tp.Type[strcs.NotSpecified], /, prefix: tp.Optional[str]
) -> strcs.ConvertResponse:
    if val is strcs.NotSpecified:
        val = ""
    return {"val": (prefix or "") + val}


describe "Scenario 2":

    it "can get annotated information from class definition":
        overall = reg.create(Overall, {"two": 20})
        assert asdict(overall) == {
            "one": {"val": 12},
            "two": {"val": 30},
            "three": {"val": "stuff"},
            "four": {"val": ""},
        }

        overall = reg.create(Overall, {"one": 1, "two": 4, "three": "hi", "four": "tree"})
        assert asdict(overall) == {
            "one": {"val": 13},
            "two": {"val": 14},
            "three": {"val": "stuffhi"},
            "four": {"val": "tree"},
        }
