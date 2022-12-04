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


@define
class AnnotationField:
    type: type
    name: str


describe "resolve_types":
    it "just returns the object if it's not an attrs/dataclass/class":
        thing: object
        for thing in (None, 0, 1, [], [1], {}, {1: 2}, True, False, lambda: 1):
            assert strcs.resolve_types(thing) is thing  # type: ignore

    it "works on normal classes":

        def get_fields(cls: type) -> list[AnnotationField]:
            return [AnnotationField(type=t, name=name) for name, t in cls.__annotations__.items()]

        self.assertWorks(None, get_fields)

    it "works on attrs classes":
        self.assertWorks(define, attrs_fields)

    it "works on dataclass classes":
        self.assertWorks(dataclass, dataclass_fields)

    def assertWorks(
        self,
        decorator: tp.Callable[[type], type] | None,
        get_fields: tp.Callable[[type], tp.Iterable[IsField]],
    ) -> None:
        class One:
            one: "int"
            two: tp.Optional["str"]
            three: tp.Annotated[tp.Optional["str"], 32]
            four: tp.Annotated[str | None, 32]
            five: tp.Annotated["Stuff", 32]
            six: dict[int, "Stuff"]
            seven: tp.Annotated[dict[int, "Stuff"], 32]
            eight: tp.Callable[[int], "Stuff"]
            nine: tp.Dict[int, "Stuff"]
            ten: list["Stuff"]
            eleven: tp.List["Stuff"]
            twelve: dict["Stuff", list[tuple["Stuff", "Stuff"]]]
            thirteen: dict["Stuff", list[tuple["Stuff", "Stuff"]]] | None
            fourteen: tp.Annotated[dict["Stuff", list[tuple["Stuff", "Stuff"]]] | None, 56]

        if decorator:
            decorated_One = decorator(One)
        else:
            decorated_One = One

        fields = {field.name: field.type for field in get_fields(decorated_One)}
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

        strcs.resolve_types(decorated_One)

        fields = {field.name: field.type for field in get_fields(decorated_One)}
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

        class Thing:
            one: "int"
            two: "str"

        if decorator:
            decorated_Thing = decorator(Thing)
        else:
            decorated_Thing = Thing

        resolved_Thing = strcs.resolve_types(decorated_Thing)

        fields = {field.name: field.type for field in get_fields(resolved_Thing)}
        assert fields["one"] is int
        assert fields["two"] is str
