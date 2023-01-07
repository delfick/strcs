# coding: spec
import dataclasses
import inspect
import sys
import typing as tp
from dataclasses import dataclass

import attrs
import pytest
from attrs import define

from strcs.disassemble import (
    Default,
    IsAnnotated,
    _Field,
    extract_annotation,
    extract_optional,
    fields_from_attrs,
    fields_from_class,
    fields_from_dataclasses,
    memoized_property,
)


def assertParams(got: tp.Sequence[_Field], want: list[_Field]):
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

    it "finds fields from looking at the init on the class when no init":

        class Thing:
            pass

        assertParams(fields_from_class(Thing), [])

    it "finds all kinds of arguments":

        class Thing:
            def __init__(
                self, blah: int, /, stuff: str, *args: str, items: tuple[int, str], **kwargs: bool
            ):
                pass

        t: tp.TypeAlias = tuple[int, str]
        assertParams(
            fields_from_class(Thing),
            [
                _Field(name="blah", type=int, kind=inspect.Parameter.POSITIONAL_ONLY),
                _Field(name="stuff", type=str, kind=inspect.Parameter.POSITIONAL_OR_KEYWORD),
                _Field(name="", type=str, kind=inspect.Parameter.VAR_POSITIONAL),
                _Field(name="items", type=t, kind=inspect.Parameter.KEYWORD_ONLY),
                _Field(name="", type=bool, kind=inspect.Parameter.VAR_KEYWORD),
            ],
        )

    it "uses object as type if unknown":

        class Thing:
            def __init__(self, blah, /, stuff, *args, items, **kwargs):
                pass

        assertParams(
            fields_from_class(Thing),
            [
                _Field(name="blah", type=object, kind=inspect.Parameter.POSITIONAL_ONLY),
                _Field(name="stuff", type=object, kind=inspect.Parameter.POSITIONAL_OR_KEYWORD),
                _Field(name="", type=object, kind=inspect.Parameter.VAR_POSITIONAL),
                _Field(name="items", type=object, kind=inspect.Parameter.KEYWORD_ONLY),
                _Field(name="", type=object, kind=inspect.Parameter.VAR_KEYWORD),
            ],
        )

    it "finds defaults":

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
            fields_from_class(Thing),
            [
                _Field(
                    name="blah",
                    type=int,
                    default=Default(1),
                    kind=inspect.Parameter.POSITIONAL_ONLY,
                ),
                _Field(
                    name="stuff",
                    type=str,
                    default=Default("asdf"),
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                ),
                _Field(name="", type=str, kind=inspect.Parameter.VAR_POSITIONAL),
                _Field(
                    name="items",
                    type=int | None,
                    default=Default(None),
                    kind=inspect.Parameter.KEYWORD_ONLY,
                ),
                _Field(name="", type=int, kind=inspect.Parameter.VAR_KEYWORD),
            ],
        )

describe "fields_from_attrs":

    it "finds no fields on class with no fields":

        @define
        class Thing:
            pass

        assertParams(fields_from_attrs(Thing), [])

    it "finds keyword only fields":

        @define
        class Thing:
            items: tuple[int, str]
            stuff: bool = attrs.field(kw_only=True)

        t: tp.TypeAlias = tuple[int, str]
        assertParams(
            fields_from_attrs(Thing),
            [
                _Field(name="items", type=t, kind=inspect.Parameter.POSITIONAL_OR_KEYWORD),
                _Field(name="stuff", type=bool, kind=inspect.Parameter.KEYWORD_ONLY),
            ],
        )

    it "finds defaults":

        @define
        class Thing:
            items: tuple[int, str] = (1, "asdf")
            stuff: bool = attrs.field(kw_only=True, default=True)

        t: tp.TypeAlias = tuple[int, str]
        assertParams(
            fields_from_attrs(Thing),
            [
                _Field(
                    name="items",
                    type=t,
                    default=Default((1, "asdf")),
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                ),
                _Field(
                    name="stuff",
                    type=bool,
                    default=Default(True),
                    kind=inspect.Parameter.KEYWORD_ONLY,
                ),
            ],
        )

    it "finds default factories":

        factory_one = lambda: (1, "asdf")
        factory_two = lambda: True

        @define
        class Thing:
            items: tuple[int, str] = attrs.field(factory=factory_one)
            stuff: bool = attrs.field(kw_only=True, factory=factory_two)

        t: tp.TypeAlias = tuple[int, str]
        assertParams(
            fields_from_attrs(Thing),
            [
                _Field(
                    name="items",
                    type=t,
                    default=factory_one,
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                ),
                _Field(
                    name="stuff",
                    type=bool,
                    default=factory_two,
                    kind=inspect.Parameter.KEYWORD_ONLY,
                ),
            ],
        )

    it "excludes fields that aren't in init":
        factory_one = lambda: (1, "asdf")
        factory_two = lambda: True

        @define
        class Thing:
            items: tuple[int, str] = attrs.field(factory=factory_one)
            stuff: bool = attrs.field(kw_only=True, factory=factory_two)
            missed: str = attrs.field(init=False, default="three")
            missed2: str = attrs.field(init=False)

        t: tp.TypeAlias = tuple[int, str]
        assertParams(
            fields_from_attrs(Thing),
            [
                _Field(
                    name="items",
                    type=t,
                    default=factory_one,
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                ),
                _Field(
                    name="stuff",
                    type=bool,
                    default=factory_two,
                    kind=inspect.Parameter.KEYWORD_ONLY,
                ),
            ],
        )

    it "renames private variables":

        @define
        class Thing:
            _thing: str
            other: int

        assertParams(
            fields_from_attrs(Thing),
            [
                _Field(
                    name="thing",
                    type=str,
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                ),
                _Field(
                    name="other",
                    type=int,
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                ),
            ],
        )

        thing = Thing(thing="one", other=4)
        assert thing._thing == "one"
        assert thing.other == 4

    it "uses aliases":
        if sys.version_info < (3, 11):
            pytest.skip("pep 681 is from python 3.11")

        @define
        class Thing:
            stuff: str
            _thing: str = attrs.field(alias="wat")
            other: int = attrs.field(alias="blah")

        assertParams(
            fields_from_attrs(Thing),
            [
                _Field(
                    name="stuff",
                    type=str,
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                ),
                _Field(
                    name="wat",
                    type=str,
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                ),
                _Field(
                    name="blah",
                    type=int,
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                ),
            ],
        )

        thing = tp.cast(tp.Callable, Thing)(stuff="one", wat="blah", blah=3)
        assert thing.stuff == "one"
        assert thing._thing == "blah"
        assert thing.other == 3

    it "excludes default factories that take a self":
        factory_one = lambda: (1, "asdf")
        factory_two = lambda instance: True

        @define
        class Thing:
            items: tuple[int, str] = attrs.field(factory=factory_one)
            stuff: bool = attrs.field(
                kw_only=True, default=attrs.Factory(factory_two, takes_self=True)
            )

        t: tp.TypeAlias = tuple[int, str]
        assertParams(
            fields_from_attrs(Thing),
            [
                _Field(
                    name="items",
                    type=t,
                    default=factory_one,
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                ),
                _Field(
                    name="stuff",
                    type=bool,
                    kind=inspect.Parameter.KEYWORD_ONLY,
                ),
            ],
        )

    it "uses object as type if unknown":

        @define
        class Thing:
            blah = attrs.field()
            stuff = attrs.field(kw_only=True)

        assertParams(
            fields_from_attrs(Thing),
            [
                _Field(name="blah", type=object, kind=inspect.Parameter.POSITIONAL_OR_KEYWORD),
                _Field(name="stuff", type=object, kind=inspect.Parameter.KEYWORD_ONLY),
            ],
        )

describe "fields_from_dataclasses":

    it "finds no fields on class with no fields":

        @dataclass
        class Thing:
            pass

        assertParams(fields_from_dataclasses(Thing), [])

    it "finds keyword only fields":

        @dataclass
        class Thing:
            items: tuple[int, str]
            stuff: bool = dataclasses.field(kw_only=True)

        t: tp.TypeAlias = tuple[int, str]
        assertParams(
            fields_from_dataclasses(Thing),
            [
                _Field(name="items", type=t, kind=inspect.Parameter.POSITIONAL_OR_KEYWORD),
                _Field(name="stuff", type=bool, kind=inspect.Parameter.KEYWORD_ONLY),
            ],
        )

    it "finds defaults":

        @dataclass
        class Thing:
            items: tuple[int, str] = (1, "asdf")
            stuff: bool = dataclasses.field(kw_only=True, default=True)

        t: tp.TypeAlias = tuple[int, str]
        assertParams(
            fields_from_dataclasses(Thing),
            [
                _Field(
                    name="items",
                    type=t,
                    default=Default((1, "asdf")),
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                ),
                _Field(
                    name="stuff",
                    type=bool,
                    default=Default(True),
                    kind=inspect.Parameter.KEYWORD_ONLY,
                ),
            ],
        )

    it "finds default factories":

        factory_one = lambda: (1, "asdf")
        factory_two = lambda: True

        @dataclass
        class Thing:
            items: tuple[int, str] = dataclasses.field(default_factory=factory_one)
            stuff: bool = dataclasses.field(kw_only=True, default_factory=factory_two)

        t: tp.TypeAlias = tuple[int, str]
        assertParams(
            fields_from_dataclasses(Thing),
            [
                _Field(
                    name="items",
                    type=t,
                    default=factory_one,
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                ),
                _Field(
                    name="stuff",
                    type=bool,
                    default=factory_two,
                    kind=inspect.Parameter.KEYWORD_ONLY,
                ),
            ],
        )

    it "excludes fields that aren't in init":
        factory_one = lambda: (1, "asdf")
        factory_two = lambda: True

        @dataclass
        class Thing:
            items: tuple[int, str] = dataclasses.field(default_factory=factory_one)
            stuff: bool = dataclasses.field(kw_only=True, default_factory=factory_two)
            missed: str = dataclasses.field(init=False, default="three")
            missed2: str = dataclasses.field(init=False)

        t: tp.TypeAlias = tuple[int, str]
        assertParams(
            fields_from_dataclasses(Thing),
            [
                _Field(
                    name="items",
                    type=t,
                    default=factory_one,
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                ),
                _Field(
                    name="stuff",
                    type=bool,
                    default=factory_two,
                    kind=inspect.Parameter.KEYWORD_ONLY,
                ),
            ],
        )

    it "doesn't rename private variables":

        @dataclass
        class Thing:
            _thing: str
            other: int

        assertParams(
            fields_from_dataclasses(Thing),
            [
                _Field(
                    name="_thing",
                    type=str,
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                ),
                _Field(
                    name="other",
                    type=int,
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                ),
            ],
        )

        thing = Thing(_thing="one", other=4)
        assert thing._thing == "one"
        assert thing.other == 4


describe "memoized_property":
    it "memoizes":
        called: list[int] = []

        class Thing:
            @memoized_property
            def blah(self) -> str:
                called.append(1)
                return "stuff"

        thing = Thing()
        assert thing.blah == "stuff"
        assert called == [1]
        assert thing.blah == "stuff"
        assert called == [1]
        assert thing.blah == "stuff"
        assert called == [1]

    it "allows setting the value":
        called: list[int] = []

        class Thing:
            @memoized_property
            def blah(self) -> str:
                called.append(1)
                return "stuff"

        thing = Thing()
        assert thing.blah == "stuff"
        assert called == [1]
        thing.blah = "other"
        assert thing.blah == "other"
        assert called == [1]
        assert thing.blah == "other"
        assert called == [1]

    it "allows deleting the value":
        called: list[int] = []

        class Thing:
            @memoized_property
            def blah(self) -> str:
                called.append(1)
                return "stuff"

        thing = Thing()
        assert thing.blah == "stuff"
        assert called == [1]
        del thing.blah
        assert thing.blah == "stuff"
        assert called == [1, 1]
        assert thing.blah == "stuff"
        assert called == [1, 1]

    it "keeps the type annotation":

        class Thing:
            @memoized_property
            def blah(self) -> str:
                return "stuff"

        def a(things: str) -> None:
            pass

        # will make mypy complain if it's broken
        a(Thing().blah)

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
            "stuff",
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

    it "returns inner most annotation when nested":
        assert extract_annotation(tp.Annotated[tp.Annotated[int, "other"], "stuff"]) == (
            int,
            tp.Annotated[int, "other", "stuff"],
            "other",
        )
