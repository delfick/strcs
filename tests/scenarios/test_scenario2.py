from typing import Annotated

import attrs

import strcs

reg = strcs.CreateRegister()
creator = reg.make_decorator()


@attrs.define(frozen=True)
class NumberAnnotation(strcs.MetaAnnotation):
    add: int


@attrs.define(frozen=True)
class SentenceAnnotation(strcs.MergedMetaAnnotation):
    prefix: str


@attrs.define
class Number:
    val: int


@attrs.define
class Sentence:
    val: str


@attrs.define
class Overall:
    one: Annotated[Number, NumberAnnotation(add=12)]
    two: Annotated[Number, NumberAnnotation(add=10)]

    three: Annotated[Sentence, SentenceAnnotation(prefix="stuff")]
    four: Sentence


@creator(Number)
def create_number(value: object, /, ann: NumberAnnotation) -> dict | None:
    if not isinstance(value, int):
        value = 0
    return {"val": value + ann.add}


@creator(Sentence)
def create_sentence(value: object, /, prefix: str | None) -> dict | None:
    if not isinstance(value, str):
        value = ""
    return {"val": (prefix or "") + value}


class TestScenario2:
    def test_it_can_get_annotated_information_from_class_definition(self):
        overall = reg.create(Overall, {"two": 20})
        assert attrs.asdict(overall) == {
            "one": {"val": 12},
            "two": {"val": 30},
            "three": {"val": "stuff"},
            "four": {"val": ""},
        }

        overall = reg.create(Overall, {"one": 1, "two": 4, "three": "hi", "four": "tree"})
        assert attrs.asdict(overall) == {
            "one": {"val": 13},
            "two": {"val": 14},
            "three": {"val": "stuffhi"},
            "four": {"val": "tree"},
        }
