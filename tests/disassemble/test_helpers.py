# coding: spec
import dataclasses
import inspect
import sys
import typing as tp

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


def assertParams(got: tp.Sequence[strcs.Field], want: list[strcs.Field]):
    print("GOT :")
    for i, g in enumerate(got):
        print("  ", i, ": ", g)
    print("WANT:")
    for i, w in enumerate(want):
        print("  ", i, ": ", w)
    assert len(want) == len(got), got
    for w, g in zip(want, got):
        assert g == w


describe "fields_from_class":

    it "finds fields from looking at the init on the class when no init", type_cache: strcs.TypeCache:

        class Thing:
            pass

        assertParams(fields_from_class(type_cache, Thing), [])

    it "finds all kinds of arguments", type_cache: strcs.TypeCache, Dis: Disassembler:

        class Thing:
            def __init__(
                self, blah: int, /, stuff: str, *args: str, items: tuple[int, str], **kwargs: bool
            ):
                pass

        t: tp.TypeAlias = tuple[int, str]
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
                    disassembled_type=Dis(t),
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

    it "uses object as type if unknown", type_cache: strcs.TypeCache, Dis: Disassembler:

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

    it "finds defaults", type_cache: strcs.TypeCache, Dis: Disassembler:

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

    it "doesn't fail on builtin functions", type_cache: strcs.TypeCache:
        with pytest.raises(ValueError):
            inspect.signature(str)

        assert fields_from_class(type_cache, str) == []

describe "fields_from_attrs":

    it "finds no fields on class with no fields", type_cache: strcs.TypeCache:

        @attrs.define
        class Thing:
            pass

        assertParams(fields_from_attrs(type_cache, Thing), [])

    it "finds keyword only fields", type_cache: strcs.TypeCache, Dis: Disassembler:

        @attrs.define
        class Thing:
            items: tuple[int, str]
            stuff: bool = attrs.field(kw_only=True)

        t: tp.TypeAlias = tuple[int, str]
        assertParams(
            fields_from_attrs(type_cache, Thing),
            [
                strcs.Field(
                    name="items",
                    owner=Thing,
                    disassembled_type=Dis(t),
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

    it "finds defaults", type_cache: strcs.TypeCache, Dis: Disassembler:

        @attrs.define
        class Thing:
            items: tuple[int, str] = (1, "asdf")
            stuff: bool = attrs.field(kw_only=True, default=True)

        t: tp.TypeAlias = tuple[int, str]
        assertParams(
            fields_from_attrs(type_cache, Thing),
            [
                strcs.Field(
                    name="items",
                    disassembled_type=Dis(t),
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

    it "finds default factories", type_cache: strcs.TypeCache, Dis: Disassembler:

        factory_one = lambda: (1, "asdf")
        factory_two = lambda: True

        @attrs.define
        class Thing:
            items: tuple[int, str] = attrs.field(factory=factory_one)
            stuff: bool = attrs.field(kw_only=True, factory=factory_two)

        t: tp.TypeAlias = tuple[int, str]
        assertParams(
            fields_from_attrs(type_cache, Thing),
            [
                strcs.Field(
                    name="items",
                    disassembled_type=Dis(t),
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

    it "excludes fields that aren't in init", type_cache: strcs.TypeCache, Dis: Disassembler:
        factory_one = lambda: (1, "asdf")
        factory_two = lambda: True

        @attrs.define
        class Thing:
            items: tuple[int, str] = attrs.field(factory=factory_one)
            stuff: bool = attrs.field(kw_only=True, factory=factory_two)
            missed: str = attrs.field(init=False, default="three")
            missed2: str = attrs.field(init=False)

        t: tp.TypeAlias = tuple[int, str]
        assertParams(
            fields_from_attrs(type_cache, Thing),
            [
                strcs.Field(
                    name="items",
                    disassembled_type=Dis(t),
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

    it "renames private variables", type_cache: strcs.TypeCache, Dis: Disassembler:

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

    it "uses aliases", type_cache: strcs.TypeCache, Dis: Disassembler:
        if sys.version_info < (3, 11):
            pytest.skip("pep 681 is from python 3.11")

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

        thing = tp.cast(tp.Callable, Thing)(stuff="one", wat="blah", blah=3)
        assert thing.stuff == "one"
        assert thing._thing == "blah"
        assert thing.other == 3

    it "excludes default factories that take a self", type_cache: strcs.TypeCache, Dis: Disassembler:
        factory_one = lambda: (1, "asdf")
        factory_two = lambda instance: True

        @attrs.define
        class Thing:
            items: tuple[int, str] = attrs.field(factory=factory_one)
            stuff: bool = attrs.field(
                kw_only=True, default=attrs.Factory(factory_two, takes_self=True)
            )

        t: tp.TypeAlias = tuple[int, str]
        assertParams(
            fields_from_attrs(type_cache, Thing),
            [
                strcs.Field(
                    name="items",
                    disassembled_type=Dis(t),
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

    it "uses object as type if unknown", type_cache: strcs.TypeCache, Dis: Disassembler:

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

describe "fields_from_dataclasses":

    it "finds no fields on class with no fields", type_cache: strcs.TypeCache:

        @dataclasses.dataclass
        class Thing:
            pass

        assertParams(fields_from_dataclasses(type_cache, Thing), [])

    it "finds keyword only fields", type_cache: strcs.TypeCache, Dis: Disassembler:

        @dataclasses.dataclass
        class Thing:
            items: tuple[int, str]
            stuff: bool = dataclasses.field(kw_only=True)

        t: tp.TypeAlias = tuple[int, str]
        assertParams(
            fields_from_dataclasses(type_cache, Thing),
            [
                strcs.Field(
                    name="items",
                    owner=Thing,
                    disassembled_type=Dis(t),
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

    it "finds defaults", type_cache: strcs.TypeCache, Dis: Disassembler:

        @dataclasses.dataclass
        class Thing:
            items: tuple[int, str] = (1, "asdf")
            stuff: bool = dataclasses.field(kw_only=True, default=True)

        t: tp.TypeAlias = tuple[int, str]
        assertParams(
            fields_from_dataclasses(type_cache, Thing),
            [
                strcs.Field(
                    name="items",
                    disassembled_type=Dis(t),
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

    it "finds default factories", type_cache: strcs.TypeCache, Dis: Disassembler:

        factory_one = lambda: (1, "asdf")
        factory_two = lambda: True

        @dataclasses.dataclass
        class Thing:
            items: tuple[int, str] = dataclasses.field(default_factory=factory_one)
            stuff: bool = dataclasses.field(kw_only=True, default_factory=factory_two)

        t: tp.TypeAlias = tuple[int, str]
        assertParams(
            fields_from_dataclasses(type_cache, Thing),
            [
                strcs.Field(
                    name="items",
                    disassembled_type=Dis(t),
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

    it "excludes fields that aren't in init", type_cache: strcs.TypeCache, Dis: Disassembler:
        factory_one = lambda: (1, "asdf")
        factory_two = lambda: True

        @dataclasses.dataclass
        class Thing:
            items: tuple[int, str] = dataclasses.field(default_factory=factory_one)
            stuff: bool = dataclasses.field(kw_only=True, default_factory=factory_two)
            missed: str = dataclasses.field(init=False, default="three")
            missed2: str = dataclasses.field(init=False)

        t: tp.TypeAlias = tuple[int, str]
        assertParams(
            fields_from_dataclasses(type_cache, Thing),
            [
                strcs.Field(
                    name="items",
                    disassembled_type=Dis(t),
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

    it "doesn't rename private variables", type_cache: strcs.TypeCache, Dis: Disassembler:

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


describe "IsAnnotated":
    it "knows if something is annotated":
        assert not IsAnnotated.has(int)
        assert not IsAnnotated.has(int | None)
        assert not IsAnnotated.has(list[int])
        assert IsAnnotated.has(tp.Annotated[int, "stuff"])
        assert IsAnnotated.has(tp.Annotated[int | None, "stuff"])
        assert IsAnnotated.has(tp.Annotated[list[int], "stuff"])

describe "extract_optional":
    it "can extract the outer most optional":
        assert extract_optional(int) == (False, int)
        assert extract_optional(tp.Annotated[int, "stuff"]) == (False, tp.Annotated[int, "stuff"])
        assert extract_optional(int | None) == (True, int)
        assert extract_optional(tp.Optional[int]) == (True, int)
        assert extract_optional(tp.Optional[tp.Annotated[int, "stuff"]]) == (
            True,
            tp.Annotated[int, "stuff"],
        )
        assert extract_optional(tp.Optional[int | str]) == (True, int | str)
        assert extract_optional(int | str | None) == (True, int | str)
        assert extract_optional(int | str) == (False, int | str)
        assert extract_optional(list[int | None] | None) == (True, list[int | None])
        assert extract_optional(list[int | None]) == (False, list[int | None])

        assert extract_optional(tp.Annotated[list[int | None] | None, "stuff"]) == (
            False,
            tp.Annotated[list[int | None] | None, "stuff"],
        )
        assert extract_optional(tp.Annotated[list[int | None], "stuff"]) == (
            False,
            tp.Annotated[list[int | None], "stuff"],
        )

describe "extract_annotation":
    it "extracts the outer most annotation":
        assert extract_annotation(tp.Annotated[int, "stuff"]) == (
            int,
            tp.Annotated[int, "stuff"],
            ("stuff",),
        )
        assert extract_annotation(int) == (int, None, None)
        assert extract_annotation(tp.Optional[tp.Annotated[int, "stuff"]]) == (
            tp.Optional[tp.Annotated[int, "stuff"]],
            None,
            None,
        )
        assert extract_annotation(list[tp.Annotated[int, "stuff"]]) == (
            list[tp.Annotated[int, "stuff"]],
            None,
            None,
        )

    it "returns multiple annotation":
        assert extract_annotation(tp.Annotated[tp.Annotated[int, "other"], "stuff"]) == (
            int,
            tp.Annotated[int, "other", "stuff"],
            ("other", "stuff"),
        )
