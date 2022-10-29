# coding: spec

from dataclasses import dataclass, fields as dataclass_fields
from attrs import define, fields as attrs_fields
import typing as tp
import strcs


class Stuff:
    two: str


class IsField(tp.Protocol):
    type: type
    name: str


describe "resolve_types":
    it "just returns the object if it's not an attrs/dataclass":

        class One:
            one: "int"
            stuff: "Stuff"

        for thing in (None, 0, 1, [], [1], {}, {1: 2}, True, False, One, One(), lambda: 1):
            assert strcs.resolve_types(thing) is thing

    it "works on attrs classes":
        self.assertWorks(define, attrs_fields)

    it "works on dataclass classes":
        self.assertWorks(dataclass, dataclass_fields)

    def assertWorks(
        self,
        decorator: tp.Callable[type, type],
        get_fields: tp.Callable[object, tp.Iterable[IsField]],
    ) -> None:
        @decorator
        class One:
            one: "int"
            two: tp.Optional["str"]
            three: tp.Annotated[tp.Optional["str"], 32]
            four: tp.Annotated[None | str, 32]
            five: tp.Annotated["Stuff", 32]
            six: dict[int, "Stuff"]
            seven: tp.Annotated[dict[int, "Stuff"], 32]
            eight: tp.Callable[[int], "Stuff"]
            nine: tp.Dict[int, "Stuff"]
            ten: list["Stuff"]
            eleven: tp.List["Stuff"]
            twelve: dict["Stuff", list[tuple["Stuff", "Stuff"]]]
            thirteen: None | dict["Stuff", list[tuple["Stuff", "Stuff"]]]
            fourteen: tp.Annotated[None | dict["Stuff", list[tuple["Stuff", "Stuff"]]], 56]

        fields = {field.name: field.type for field in get_fields(One)}
        assert fields["one"] == "int"
        assert fields["two"] == tp.Optional["str"]
        assert fields["three"] == tp.Annotated[tp.Optional["str"], 32]
        assert fields["four"] == tp.Annotated[str | None, 32]
        assert fields["five"] == tp.Annotated["Stuff", 32]
        assert fields["six"] == dict[int, "Stuff"]
        assert fields["seven"] == tp.Annotated[dict[int, "Stuff"], 32]
        assert fields["eight"] == tp.Callable[[int], "Stuff"]
        assert fields["nine"] == tp.Dict[int, "Stuff"]
        assert fields["ten"] == list["Stuff"]
        assert fields["eleven"] == tp.List["Stuff"]
        assert fields["twelve"] == dict["Stuff", list[tuple["Stuff", "Stuff"]]]
        assert fields["thirteen"] == dict["Stuff", list[tuple["Stuff", "Stuff"]]] | None
        assert (
            fields["fourteen"]
            == tp.Annotated[dict["Stuff", list[tuple["Stuff", "Stuff"]]] | None, 56]
        )

        strcs.resolve_types(One)

        fields = {field.name: field.type for field in get_fields(One)}
        assert fields["one"] == int
        assert fields["two"] == tp.Optional[str]
        assert fields["three"] == tp.Annotated[tp.Optional[str], 32]
        assert fields["four"] == tp.Annotated[str | None, 32]
        assert fields["five"] == tp.Annotated[Stuff, 32]
        assert fields["six"] == dict[int, Stuff]
        assert fields["seven"] == tp.Annotated[dict[int, Stuff], 32]
        assert fields["eight"] == tp.Callable[[int], Stuff]
        assert fields["nine"] == tp.Dict[int, Stuff]
        assert fields["ten"] == list[Stuff]
        assert fields["eleven"] == tp.List[Stuff]
        assert fields["twelve"] == dict[Stuff, list[tuple[Stuff, Stuff]]]
        assert fields["thirteen"] == dict[Stuff, list[tuple[Stuff, Stuff]]] | None
        assert fields["fourteen"] == tp.Annotated[dict[Stuff, list[tuple[Stuff, Stuff]]] | None, 56]

        @strcs.resolve_types
        @decorator
        class Thing:
            one: "int"
            two: "str"

        fields = {field.name: field.type for field in get_fields(Thing)}
        assert fields["one"] is int
        assert fields["two"] is str
