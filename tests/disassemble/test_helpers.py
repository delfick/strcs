import dataclasses
import inspect
from collections.abc import Sequence
from typing import Annotated, Optional

import attrs
import pytest

import strcs
from strcs.disassemble import (
    Default,
    IsAnnotated,
    extract_annotation,
    extract_optional,
    fields_from_attrs,
    fields_from_class,
    fields_from_dataclasses,
)

Disassembler = strcs.disassemble.Disassembler


def assertParams(got: Sequence[strcs.Field], want: list[strcs.Field]):
    print("GOT :")
    for i, g in enumerate(got):
        print("  ", i, ": ", g)
    print("WANT:")
    for i, w in enumerate(want):
        print("  ", i, ": ", w)
    assert len(want) == len(got), got
    for w, g in zip(want, got):
        assert g == w


class TestFieldsFromClass:
    def test_it_finds_fields_from_looking_at_the_init_on_the_class_when_no_init(
        self, type_cache: strcs.TypeCache
    ):
        class Thing:
            pass

        assertParams(fields_from_class(type_cache, Thing), [])

    def test_it_finds_all_kinds_of_arguments(self, type_cache: strcs.TypeCache, Dis: Disassembler):
        class Thing:
            def __init__(
                self, blah: int, /, stuff: str, *args: str, items: tuple[int, str], **kwargs: bool
            ):
                pass

        assertParams(
            fields_from_class(type_cache, Thing),
            [
                strcs.Field(
                    name="blah",
                    owner=Thing,
                    disassembled_type=Dis(int),
                    kind=inspect.Parameter.POSITIONAL_ONLY,
                ),
                strcs.Field(
                    name="stuff",
                    owner=Thing,
                    disassembled_type=Dis(str),
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                ),
                strcs.Field(
                    name="",
                    disassembled_type=Dis(str),
                    owner=Thing,
                    kind=inspect.Parameter.VAR_POSITIONAL,
                ),
                strcs.Field(
                    name="items",
                    disassembled_type=Dis(tuple[int, str]),
                    owner=Thing,
                    kind=inspect.Parameter.KEYWORD_ONLY,
                ),
                strcs.Field(
                    name="",
                    disassembled_type=Dis(bool),
                    owner=Thing,
                    kind=inspect.Parameter.VAR_KEYWORD,
                ),
            ],
        )

    def test_it_uses_object_as_type_if_unknown(
        self, type_cache: strcs.TypeCache, Dis: Disassembler
    ):
        class Thing:
            def __init__(self, blah, /, stuff, *args, items, **kwargs):
                pass

        assertParams(
            fields_from_class(type_cache, Thing),
            [
                strcs.Field(
                    name="blah",
                    disassembled_type=Dis(object),
                    owner=Thing,
                    kind=inspect.Parameter.POSITIONAL_ONLY,
                ),
                strcs.Field(
                    name="stuff",
                    disassembled_type=Dis(object),
                    owner=Thing,
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                ),
                strcs.Field(
                    name="",
                    disassembled_type=Dis(object),
                    owner=Thing,
                    kind=inspect.Parameter.VAR_POSITIONAL,
                ),
                strcs.Field(
                    name="items",
                    disassembled_type=Dis(object),
                    owner=Thing,
                    kind=inspect.Parameter.KEYWORD_ONLY,
                ),
                strcs.Field(
                    name="",
                    disassembled_type=Dis(object),
                    owner=Thing,
                    kind=inspect.Parameter.VAR_KEYWORD,
                ),
            ],
        )

    def test_it_finds_defaults(self, type_cache: strcs.TypeCache, Dis: Disassembler):
        class Thing:
            def __init__(
                self,
                blah: int = 1,
                /,
                stuff: str = "asdf",
                *args: str,
                items: int | None = None,
                **kwargs: int,
            ):
                pass

        assertParams(
            fields_from_class(type_cache, Thing),
            [
                strcs.Field(
                    name="blah",
                    disassembled_type=Dis(int),
                    owner=Thing,
                    default=Default(1),
                    kind=inspect.Parameter.POSITIONAL_ONLY,
                ),
                strcs.Field(
                    name="stuff",
                    owner=Thing,
                    disassembled_type=Dis(str),
                    default=Default("asdf"),
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                ),
                strcs.Field(
                    name="",
                    owner=Thing,
                    disassembled_type=Dis(str),
                    kind=inspect.Parameter.VAR_POSITIONAL,
                ),
                strcs.Field(
                    name="items",
                    owner=Thing,
                    disassembled_type=Dis(int | None),
                    default=Default(None),
                    kind=inspect.Parameter.KEYWORD_ONLY,
                ),
                strcs.Field(
                    name="",
                    owner=Thing,
                    disassembled_type=Dis(int),
                    kind=inspect.Parameter.VAR_KEYWORD,
                ),
            ],
        )

    def test_it_doesnt_fail_on_builtin_functions(self, type_cache: strcs.TypeCache):
        with pytest.raises(ValueError):
            inspect.signature(str)

        assert fields_from_class(type_cache, str) == []


class TestFieldsFromAttrs:
    def test_it_finds_no_fields_on_class_with_no_fields(self, type_cache: strcs.TypeCache):
        @attrs.define
        class Thing:
            pass

        assertParams(fields_from_attrs(type_cache, Thing), [])

    def test_it_finds_keyword_only_fields(self, type_cache: strcs.TypeCache, Dis: Disassembler):
        @attrs.define
        class Thing:
            items: tuple[int, str]
            stuff: bool = attrs.field(kw_only=True)

        assertParams(
            fields_from_attrs(type_cache, Thing),
            [
                strcs.Field(
                    name="items",
                    owner=Thing,
                    disassembled_type=Dis(tuple[int, str]),
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                ),
                strcs.Field(
                    name="stuff",
                    owner=Thing,
                    disassembled_type=Dis(bool),
                    kind=inspect.Parameter.KEYWORD_ONLY,
                ),
            ],
        )

    def test_it_finds_defaults(self, type_cache: strcs.TypeCache, Dis: Disassembler):
        @attrs.define
        class Thing:
            items: tuple[int, str] = (1, "asdf")
            stuff: bool = attrs.field(kw_only=True, default=True)

        assertParams(
            fields_from_attrs(type_cache, Thing),
            [
                strcs.Field(
                    name="items",
                    disassembled_type=Dis(tuple[int, str]),
                    owner=Thing,
                    default=Default((1, "asdf")),
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                ),
                strcs.Field(
                    name="stuff",
                    disassembled_type=Dis(bool),
                    owner=Thing,
                    default=Default(True),
                    kind=inspect.Parameter.KEYWORD_ONLY,
                ),
            ],
        )

    def test_it_finds_default_factories(self, type_cache: strcs.TypeCache, Dis: Disassembler):
        factory_one = lambda: (1, "asdf")
        factory_two = lambda: True

        @attrs.define
        class Thing:
            items: tuple[int, str] = attrs.field(factory=factory_one)
            stuff: bool = attrs.field(kw_only=True, factory=factory_two)

        assertParams(
            fields_from_attrs(type_cache, Thing),
            [
                strcs.Field(
                    name="items",
                    disassembled_type=Dis(tuple[int, str]),
                    owner=Thing,
                    default=factory_one,
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                ),
                strcs.Field(
                    name="stuff",
                    disassembled_type=Dis(bool),
                    owner=Thing,
                    default=factory_two,
                    kind=inspect.Parameter.KEYWORD_ONLY,
                ),
            ],
        )

    def test_it_excludes_fields_that_arent_in_init(
        self, type_cache: strcs.TypeCache, Dis: Disassembler
    ):
        factory_one = lambda: (1, "asdf")
        factory_two = lambda: True

        @attrs.define
        class Thing:
            items: tuple[int, str] = attrs.field(factory=factory_one)
            stuff: bool = attrs.field(kw_only=True, factory=factory_two)
            missed: str = attrs.field(init=False, default="three")
            missed2: str = attrs.field(init=False)

        assertParams(
            fields_from_attrs(type_cache, Thing),
            [
                strcs.Field(
                    name="items",
                    disassembled_type=Dis(tuple[int, str]),
                    owner=Thing,
                    default=factory_one,
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                ),
                strcs.Field(
                    name="stuff",
                    disassembled_type=Dis(bool),
                    owner=Thing,
                    default=factory_two,
                    kind=inspect.Parameter.KEYWORD_ONLY,
                ),
            ],
        )

    def test_it_renames_private_variables(self, type_cache: strcs.TypeCache, Dis: Disassembler):
        @attrs.define
        class Thing:
            _thing: str
            other: int

        assertParams(
            fields_from_attrs(type_cache, Thing),
            [
                strcs.Field(
                    name="thing",
                    disassembled_type=Dis(str),
                    owner=Thing,
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                ),
                strcs.Field(
                    name="other",
                    disassembled_type=Dis(int),
                    owner=Thing,
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                ),
            ],
        )

        thing = Thing(thing="one", other=4)
        assert thing._thing == "one"
        assert thing.other == 4

    def test_it_uses_aliases(self, type_cache: strcs.TypeCache, Dis: Disassembler):
        @attrs.define
        class Thing:
            stuff: str
            _thing: str = attrs.field(alias="wat")
            other: int = attrs.field(alias="blah")

        assertParams(
            fields_from_attrs(type_cache, Thing),
            [
                strcs.Field(
                    name="stuff",
                    disassembled_type=Dis(str),
                    owner=Thing,
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                ),
                strcs.Field(
                    name="wat",
                    disassembled_type=Dis(str),
                    owner=Thing,
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                ),
                strcs.Field(
                    name="blah",
                    disassembled_type=Dis(int),
                    owner=Thing,
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                ),
            ],
        )

        thing = Thing(stuff="one", wat="blah", blah=3)
        assert thing.stuff == "one"
        assert thing._thing == "blah"
        assert thing.other == 3

    def test_it_excludes_default_factories_that_take_a_self(
        self, type_cache: strcs.TypeCache, Dis: Disassembler
    ):
        factory_one = lambda: (1, "asdf")
        factory_two = lambda instance: True

        @attrs.define
        class Thing:
            items: tuple[int, str] = attrs.field(factory=factory_one)
            stuff: bool = attrs.field(
                kw_only=True, default=attrs.Factory(factory_two, takes_self=True)
            )

        assertParams(
            fields_from_attrs(type_cache, Thing),
            [
                strcs.Field(
                    name="items",
                    disassembled_type=Dis(tuple[int, str]),
                    owner=Thing,
                    default=factory_one,
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                ),
                strcs.Field(
                    name="stuff",
                    disassembled_type=Dis(bool),
                    owner=Thing,
                    kind=inspect.Parameter.KEYWORD_ONLY,
                ),
            ],
        )

    def test_it_uses_object_as_type_if_unknown(
        self, type_cache: strcs.TypeCache, Dis: Disassembler
    ):
        @attrs.define
        class Thing:
            blah = attrs.field()
            stuff = attrs.field(kw_only=True)

        assertParams(
            fields_from_attrs(type_cache, Thing),
            [
                strcs.Field(
                    name="blah",
                    disassembled_type=Dis(object),
                    owner=Thing,
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                ),
                strcs.Field(
                    name="stuff",
                    disassembled_type=Dis(object),
                    owner=Thing,
                    kind=inspect.Parameter.KEYWORD_ONLY,
                ),
            ],
        )


class TestFieldsFromDataclasses:
    def test_it_finds_no_fields_on_class_with_no_fields(self, type_cache: strcs.TypeCache):
        @dataclasses.dataclass
        class Thing:
            pass

        assertParams(fields_from_dataclasses(type_cache, Thing), [])

    def test_it_finds_keyword_only_fields(self, type_cache: strcs.TypeCache, Dis: Disassembler):
        @dataclasses.dataclass
        class Thing:
            items: tuple[int, str]
            stuff: bool = dataclasses.field(kw_only=True)

        assertParams(
            fields_from_dataclasses(type_cache, Thing),
            [
                strcs.Field(
                    name="items",
                    owner=Thing,
                    disassembled_type=Dis(tuple[int, str]),
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                ),
                strcs.Field(
                    name="stuff",
                    owner=Thing,
                    disassembled_type=Dis(bool),
                    kind=inspect.Parameter.KEYWORD_ONLY,
                ),
            ],
        )

    def test_it_finds_defaults(self, type_cache: strcs.TypeCache, Dis: Disassembler):
        @dataclasses.dataclass
        class Thing:
            items: tuple[int, str] = (1, "asdf")
            stuff: bool = dataclasses.field(kw_only=True, default=True)

        assertParams(
            fields_from_dataclasses(type_cache, Thing),
            [
                strcs.Field(
                    name="items",
                    disassembled_type=Dis(tuple[int, str]),
                    owner=Thing,
                    default=Default((1, "asdf")),
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                ),
                strcs.Field(
                    name="stuff",
                    disassembled_type=Dis(bool),
                    owner=Thing,
                    default=Default(True),
                    kind=inspect.Parameter.KEYWORD_ONLY,
                ),
            ],
        )

    def test_it_finds_default_factories(self, type_cache: strcs.TypeCache, Dis: Disassembler):
        factory_one = lambda: (1, "asdf")
        factory_two = lambda: True

        @dataclasses.dataclass
        class Thing:
            items: tuple[int, str] = dataclasses.field(default_factory=factory_one)
            stuff: bool = dataclasses.field(kw_only=True, default_factory=factory_two)

        assertParams(
            fields_from_dataclasses(type_cache, Thing),
            [
                strcs.Field(
                    name="items",
                    disassembled_type=Dis(tuple[int, str]),
                    owner=Thing,
                    default=factory_one,
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                ),
                strcs.Field(
                    name="stuff",
                    disassembled_type=Dis(bool),
                    owner=Thing,
                    default=factory_two,
                    kind=inspect.Parameter.KEYWORD_ONLY,
                ),
            ],
        )

    def test_it_excludes_fields_that_arent_in_init(
        self, type_cache: strcs.TypeCache, Dis: Disassembler
    ):
        factory_one = lambda: (1, "asdf")
        factory_two = lambda: True

        @dataclasses.dataclass
        class Thing:
            items: tuple[int, str] = dataclasses.field(default_factory=factory_one)
            stuff: bool = dataclasses.field(kw_only=True, default_factory=factory_two)
            missed: str = dataclasses.field(init=False, default="three")
            missed2: str = dataclasses.field(init=False)

        assertParams(
            fields_from_dataclasses(type_cache, Thing),
            [
                strcs.Field(
                    name="items",
                    disassembled_type=Dis(tuple[int, str]),
                    owner=Thing,
                    default=factory_one,
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                ),
                strcs.Field(
                    name="stuff",
                    disassembled_type=Dis(bool),
                    owner=Thing,
                    default=factory_two,
                    kind=inspect.Parameter.KEYWORD_ONLY,
                ),
            ],
        )

    def test_it_doesnt_rename_private_variables(
        self, type_cache: strcs.TypeCache, Dis: Disassembler
    ):
        @dataclasses.dataclass
        class Thing:
            _thing: str
            other: int

        assertParams(
            fields_from_dataclasses(type_cache, Thing),
            [
                strcs.Field(
                    name="_thing",
                    disassembled_type=Dis(str),
                    owner=Thing,
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                ),
                strcs.Field(
                    name="other",
                    disassembled_type=Dis(int),
                    owner=Thing,
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                ),
            ],
        )

        thing = Thing(_thing="one", other=4)
        assert thing._thing == "one"
        assert thing.other == 4


class TestIsAnnotated:
    def test_it_knows_if_something_is_annotated(self):
        assert not IsAnnotated.has(int)
        assert not IsAnnotated.has(int | None)
        assert not IsAnnotated.has(list[int])
        assert IsAnnotated.has(Annotated[int, "stuff"])
        assert IsAnnotated.has(Annotated[int | None, "stuff"])
        assert IsAnnotated.has(Annotated[list[int], "stuff"])


class TestExtractOptional:
    def test_it_can_extract_the_outer_most_optional(self):
        assert extract_optional(int) == (False, int)
        assert extract_optional(Annotated[int, "stuff"]) == (False, Annotated[int, "stuff"])
        assert extract_optional(int | None) == (True, int)
        assert extract_optional(Optional[int]) == (True, int)
        assert extract_optional(Optional[Annotated[int, "stuff"]]) == (
            True,
            Annotated[int, "stuff"],
        )
        assert extract_optional(Optional[int | str]) == (True, int | str)
        assert extract_optional(int | str | None) == (True, int | str)
        assert extract_optional(int | str) == (False, int | str)
        assert extract_optional(list[int | None] | None) == (True, list[int | None])
        assert extract_optional(list[int | None]) == (False, list[int | None])

        assert extract_optional(Annotated[list[int | None] | None, "stuff"]) == (
            False,
            Annotated[list[int | None] | None, "stuff"],
        )
        assert extract_optional(Annotated[list[int | None], "stuff"]) == (
            False,
            Annotated[list[int | None], "stuff"],
        )


class TestExtractAnnotation:
    def test_it_extracts_the_outer_most_annotation(self):
        assert extract_annotation(Annotated[int, "stuff"]) == (
            int,
            Annotated[int, "stuff"],
            ("stuff",),
        )
        assert extract_annotation(int) == (int, None, None)
        assert extract_annotation(Optional[Annotated[int, "stuff"]]) == (
            Optional[Annotated[int, "stuff"]],
            None,
            None,
        )
        assert extract_annotation(list[Annotated[int, "stuff"]]) == (
            list[Annotated[int, "stuff"]],
            None,
            None,
        )

    def test_it_returns_multiple_annotation(self):
        assert extract_annotation(Annotated[Annotated[int, "other"], "stuff"]) == (
            int,
            Annotated[int, "other", "stuff"],
            ("other", "stuff"),
        )
