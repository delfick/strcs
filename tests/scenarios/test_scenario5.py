# coding: spec

from attrs import define
import typing as tp
import cattrs
import strcs


reg = strcs.CreateRegister()
creator = reg.make_decorator()


@define
class Sentences:
    one: str
    two: str
    three: str


@creator(Sentences)
def create_sentences(val: str) -> strcs.ConvertResponse:
    parts = val.split(",")
    return {"one": parts[0], "two": parts[1], "three": parts[2]}


describe "can use the original converter":

    it "works":
        converter = cattrs.Converter()

        def reverse_strings(o: tp.Any, _: tp.Any) -> str:
            if isinstance(o, str):
                return "".join(reversed(o))
            else:
                raise Exception("no")

        converter.register_structure_hook(str, reverse_strings)
        meta = strcs.Meta(converter=converter)

        sentences = reg.create(Sentences, "hello,there,tree", meta=meta)
        assert isinstance(sentences, Sentences)
        assert sentences.one == "olleh"
        assert sentences.two == "ereht"
        assert sentences.three == "eert"
