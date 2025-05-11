import dataclasses
from collections.abc import Callable, Iterable
from typing import Annotated, Optional, Protocol

import attrs

import strcs


class Stuff:
    two: str


class IsField(Protocol):
    type: type
    name: str


@attrs.define
class AnnotationField:
    type: type
    name: str


class TestResolveTypes:
    def test_it_just_returns_the_object_if_its_not_an_attrs_dataclass_class(self) -> None:
        thing: object
        for thing in (None, 0, 1, [], [1], {}, {1: 2}, True, False, lambda: 1):
            assert (
                strcs.resolve_types(  # type: ignore[type-var]
                    thing,  # type: ignore[arg-type]
                    type_cache=strcs.TypeCache(),
                )
                is thing
            )

    def test_it_clears_the_type_cache(self) -> None:
        type_cache = strcs.TypeCache()

        class What:
            pass

        class Thing:
            what: "What"

        assert len(type_cache) == 0

        type_cache.disassemble(Thing)

        assert len(type_cache) > 0

        strcs.resolve_types(Thing, type_cache=type_cache, globalns=locals(), localns=locals())

        assert len(type_cache) == 0

    def assertWorks(
        self,
        decorator: Callable[[type], type] | None,
        get_fields: Callable[[type], Iterable[IsField]],
    ) -> None:
        class One:
            one: "int"
            two: Optional["str"]
            three: Annotated[Optional["str"], 32]
            four: Annotated[str | None, 32]
            five: Annotated["Stuff", 32]
            six: dict[int, "Stuff"]
            seven: Annotated[dict[int, "Stuff"], 32]
            eight: Callable[[int], "Stuff"]
            nine: dict[int, "Stuff"]
            ten: list["Stuff"]
            eleven: list["Stuff"]
            twelve: dict["Stuff", list[tuple["Stuff", "Stuff"]]]
            thirteen: dict["Stuff", list[tuple["Stuff", "Stuff"]]] | None
            fourteen: Annotated[dict["Stuff", list[tuple["Stuff", "Stuff"]]] | None, 56]

        if decorator:
            decorated_One = decorator(One)
        else:
            decorated_One = One

        fields = {field.name: field.type for field in get_fields(decorated_One)}
        assert fields["one"] == "int"
        assert fields["two"] == Optional["str"]
        assert fields["three"] == Annotated[Optional["str"], 32]
        assert fields["four"] == Annotated[str | None, 32]
        assert fields["five"] == Annotated["Stuff", 32]
        assert fields["six"] == dict[int, "Stuff"]
        assert fields["seven"] == Annotated[dict[int, "Stuff"], 32]
        assert fields["eight"] == Callable[[int], "Stuff"]
        assert fields["nine"] == dict[int, "Stuff"]
        assert fields["ten"] == list["Stuff"]
        assert fields["eleven"] == list["Stuff"]
        assert fields["twelve"] == dict["Stuff", list[tuple["Stuff", "Stuff"]]]
        assert fields["thirteen"] == dict["Stuff", list[tuple["Stuff", "Stuff"]]] | None
        assert (
            fields["fourteen"]
            == Annotated[dict["Stuff", list[tuple["Stuff", "Stuff"]]] | None, 56]
        )

        strcs.resolve_types(decorated_One, type_cache=strcs.TypeCache())

        fields = {field.name: field.type for field in get_fields(decorated_One)}
        assert fields["one"] == int
        assert fields["two"] == Optional[str]
        assert fields["three"] == Annotated[str | None, 32]
        assert fields["four"] == Annotated[str | None, 32]
        assert fields["five"] == Annotated[Stuff, 32]
        assert fields["six"] == dict[int, Stuff]
        assert fields["seven"] == Annotated[dict[int, Stuff], 32]
        assert fields["eight"] == Callable[[int], Stuff]
        assert fields["nine"] == dict[int, Stuff]
        assert fields["ten"] == list[Stuff]
        assert fields["eleven"] == list[Stuff]
        assert fields["twelve"] == dict[Stuff, list[tuple[Stuff, Stuff]]]
        assert fields["thirteen"] == dict[Stuff, list[tuple[Stuff, Stuff]]] | None
        assert fields["fourteen"] == Annotated[dict[Stuff, list[tuple[Stuff, Stuff]]] | None, 56]

        class Thing:
            one: "int"
            two: "str"

        if decorator:
            decorated_Thing = decorator(Thing)
        else:
            decorated_Thing = Thing

        resolved_Thing = strcs.resolve_types(decorated_Thing, type_cache=strcs.TypeCache())

        fields = {field.name: field.type for field in get_fields(resolved_Thing)}
        assert fields["one"] is int
        assert fields["two"] is str

    def test_it_works_on_normal_classes(self):
        def get_fields(cls: type) -> list[AnnotationField]:
            return [AnnotationField(type=t, name=name) for name, t in cls.__annotations__.items()]

        self.assertWorks(None, get_fields)

    def test_it_works_on_attrs_classes(self):
        self.assertWorks(attrs.define, attrs.fields)

    def test_it_works_on_dataclass_classes(self):
        self.assertWorks(dataclasses.dataclass, dataclasses.fields)

    def test_it_finds_via_properties(self) -> None:
        @attrs.define
        class One:
            one: "int"
            two: Optional["str"]
            three: Annotated[Optional["str"], 32]

        @attrs.define
        class Holder:
            one: "One"

        fields = {field.name: field.type for field in attrs.fields(Holder)}
        assert fields["one"] == "One"

        fields = {field.name: field.type for field in attrs.fields(One)}
        assert fields["one"] == "int"
        assert fields["two"] == Optional["str"]
        assert fields["three"] == Annotated[Optional["str"], 32]

        strcs.resolve_types(Holder, globals(), locals(), type_cache=strcs.TypeCache())

        fields = {field.name: field.type for field in attrs.fields(Holder)}
        assert fields["one"] is One

        fields = {field.name: field.type for field in attrs.fields(One)}
        assert fields["one"] == int
        assert fields["two"] == Optional[str]
        assert fields["three"] == Annotated[str | None, 32]

    def test_it_finds_via_optional_properties(self) -> None:
        @attrs.define
        class One:
            one: "int"
            two: Optional["str"]
            three: Annotated[Optional["str"], 32]

        @attrs.define
        class Holder:
            one: Optional["One"]

        fields = {field.name: field.type for field in attrs.fields(Holder)}
        assert fields["one"] == Optional["One"]

        fields = {field.name: field.type for field in attrs.fields(One)}
        assert fields["one"] == "int"
        assert fields["two"] == Optional["str"]
        assert fields["three"] == Annotated[Optional["str"], 32]

        strcs.resolve_types(Holder, globals(), locals(), type_cache=strcs.TypeCache())

        fields = {field.name: field.type for field in attrs.fields(Holder)}
        assert fields["one"] == One | None

        fields = {field.name: field.type for field in attrs.fields(One)}
        assert fields["one"] == int
        assert fields["two"] == Optional[str]
        assert fields["three"] == Annotated[str | None, 32]

    def test_it_finds_via_annotated_properties(self) -> None:
        @attrs.define
        class One:
            one: "int"
            two: Optional["str"]
            three: Annotated[Optional["str"], 32]

        @attrs.define
        class Two:
            one: "str"

        @attrs.define
        class Three:
            four: "Four"

        @attrs.define
        class Four:
            one: "bool"

        @attrs.define
        class Holder:
            one: Optional["One"]
            two: Annotated[Optional["Two"], "hi"]
            three: Annotated["Three", "hi"] | None

        fields = {field.name: field.type for field in attrs.fields(Holder)}
        assert fields["one"] == Optional["One"]
        assert fields["two"] == Annotated[Optional["Two"], "hi"]
        assert fields["three"] == Optional[Annotated["Three", "hi"]]

        fields = {field.name: field.type for field in attrs.fields(One)}
        assert fields["one"] == "int"
        assert fields["two"] == Optional["str"]
        assert fields["three"] == Annotated[Optional["str"], 32]

        fields = {field.name: field.type for field in attrs.fields(Two)}
        assert fields["one"] == "str"

        fields = {field.name: field.type for field in attrs.fields(Three)}
        assert fields["four"] == "Four"

        fields = {field.name: field.type for field in attrs.fields(Four)}
        assert fields["one"] == "bool"

        strcs.resolve_types(Holder, globals(), locals(), type_cache=strcs.TypeCache())

        fields = {field.name: field.type for field in attrs.fields(Holder)}
        assert fields["one"] == One | None
        assert fields["two"] == Annotated[Two | None, "hi"]
        assert fields["three"] == Optional[Annotated[Three, "hi"]]

        fields = {field.name: field.type for field in attrs.fields(One)}
        assert fields["one"] == int
        assert fields["two"] == str | None
        assert fields["three"] == Annotated[str | None, 32]

        fields = {field.name: field.type for field in attrs.fields(Two)}
        assert fields["one"] == str

        fields = {field.name: field.type for field in attrs.fields(Three)}
        assert fields["four"] == Four

        fields = {field.name: field.type for field in attrs.fields(Four)}
        assert fields["one"] == bool
