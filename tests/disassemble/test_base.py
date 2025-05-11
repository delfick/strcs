import dataclasses
import functools
import inspect
import re
import types
from collections import OrderedDict
from collections.abc import Callable
from typing import Annotated, Generic, NewType, Optional, TypeVar, Union

import attrs
import pytest

import strcs
from strcs import Field, InstanceCheckMeta, Type, resolve_types
from strcs.disassemble import (
    Default,
    fields_from_attrs,
    fields_from_class,
    fields_from_dataclasses,
)

from .test_helpers import assertParams

Disassembler = strcs.disassemble.Disassembler


class Partial:
    got: object
    equals: bool

    def __init__(self, func: Callable, *args: object):
        self.func = func
        self.args = args

    def __eq__(self, got: object) -> bool:
        self.got = got
        self.equals = False

        if not isinstance(self.got, functools.partial):
            return False
        if self.got.func is not self.func:
            return False
        if self.got.args != self.args:
            return False

        self.equals = True
        return True

    def __repr__(self) -> str:
        if not hasattr(self, "got") or not hasattr(self, "equals"):
            return f"<Partial {self.func}:{self.args} />"

        return repr(self.got)


T = TypeVar("T")
U = TypeVar("U")


class TestType:
    def test_it_works_on_None(self, type_cache: strcs.TypeCache):
        provided = None
        disassembled = Type.create(provided, expect=type(None), cache=type_cache)
        assert disassembled.original is provided
        assert disassembled.optional is False
        assert disassembled.extracted is None
        assert not disassembled.is_type_alias
        assert not disassembled.is_type_alias
        assert disassembled.origin == type(None)
        assert disassembled.origin_type == type(None)
        nun = None
        assert disassembled.checkable == nun and isinstance(
            disassembled.checkable, InstanceCheckMeta
        )
        assert disassembled.annotations is None
        assert disassembled.annotated is None
        assert not disassembled.is_annotated
        assert disassembled.without_annotation is None
        assert disassembled.without_optional is None
        assert disassembled.nonoptional_union_types == ()
        assert disassembled.fields == []
        assert disassembled.fields_from == type(None)
        assert disassembled.fields_getter is None
        assert not attrs.has(disassembled.checkable)
        assert not dataclasses.is_dataclass(disassembled.checkable)
        assert disassembled.is_type_for(None)
        assert not disassembled.is_type_for(1)
        assert disassembled.is_equivalent_type_for(None)

        assert disassembled.for_display() == "None"

    def test_it_doesnt_overcome_python_limitations_with_annotating_None_and_thinks_we_annotated_type_of_None(
        self, type_cache: strcs.TypeCache
    ):
        provided = Annotated[None, 1]
        disassembled = Type.create(provided, expect=type(None), cache=type_cache)
        assert disassembled.original is provided
        assert disassembled.optional is False
        assert disassembled.extracted == type(None)
        assert not disassembled.is_type_alias
        assert not disassembled.is_type_alias
        assert disassembled.origin == type(None)
        assert disassembled.origin_type == type(None)
        assert disassembled.checkable == type(None) and isinstance(
            disassembled.checkable, InstanceCheckMeta
        )
        assert disassembled.annotations == (1,)
        assert disassembled.annotated is provided
        assert disassembled.is_annotated
        assert disassembled.without_annotation == type(None)
        assert disassembled.without_optional == provided
        assert disassembled.nonoptional_union_types == ()
        assert disassembled.fields == []
        assert disassembled.fields_from == type(None)
        assert disassembled.fields_getter == Partial(fields_from_class, type_cache)
        assert not attrs.has(disassembled.checkable)
        assert not dataclasses.is_dataclass(disassembled.checkable)
        assert disassembled.is_type_for(None)
        assert not disassembled.is_type_for(1)
        assert disassembled.is_equivalent_type_for(None)

        assert disassembled.for_display() == "Annotated[NoneType, 1]"

    def test_it_works_on_simple_type(self, type_cache: strcs.TypeCache):
        provided = int
        disassembled = Type.create(provided, expect=int, cache=type_cache)
        assert disassembled.original is provided
        assert disassembled.optional is False
        assert disassembled.extracted == int
        assert not disassembled.is_type_alias
        assert disassembled.origin == int
        assert disassembled.origin_type == int
        assert disassembled.checkable == int and isinstance(
            disassembled.checkable, InstanceCheckMeta
        )
        assert issubclass(int, provided)
        assert issubclass(int, disassembled.checkable)
        assert disassembled.is_equivalent_type_for(int)

        assert disassembled.annotations is None
        assert disassembled.annotated is None
        assert not disassembled.is_annotated
        assert disassembled.without_annotation == int
        assert disassembled.without_optional == int
        assert disassembled.nonoptional_union_types == ()
        assert disassembled.fields == []
        assert disassembled.fields_from == int
        assert disassembled.fields_getter is None
        assert not attrs.has(disassembled.checkable)
        assert not dataclasses.is_dataclass(disassembled.checkable)
        assert disassembled.is_type_for(1)
        assert not disassembled.is_type_for(None)
        assert disassembled.is_equivalent_type_for(3)

        assert disassembled.for_display() == "int"

    def test_it_works_on_a_union(self, type_cache: strcs.TypeCache):
        provided = int | str
        disassembled = Type.create(provided, expect=types.UnionType, cache=type_cache)
        assert disassembled.original is provided
        assert disassembled.optional is False
        assert disassembled.extracted == int | str
        assert not disassembled.is_type_alias
        assert disassembled.origin == types.UnionType
        assert disassembled.origin_type == types.UnionType
        assert disassembled.checkable == int and isinstance(
            disassembled.checkable, InstanceCheckMeta
        )
        assert disassembled.annotations is None
        assert disassembled.annotated is None
        assert disassembled.mro.all_vars == ()
        assert not disassembled.is_annotated
        assert disassembled.without_annotation == int | str
        assert disassembled.without_optional == int | str
        assert disassembled.nonoptional_union_types == (str, int)
        assert disassembled.fields == []
        assert disassembled.fields_from == int | str
        assert disassembled.fields_getter is None
        assert not attrs.has(disassembled.checkable)
        assert not dataclasses.is_dataclass(disassembled.checkable)
        assert disassembled.is_type_for(1)
        assert disassembled.is_type_for("asdf")
        assert not disassembled.is_type_for(None)
        assert disassembled.is_equivalent_type_for(3)
        assert disassembled.is_equivalent_type_for("asdf")

        assert disassembled.for_display() == "str | int"

    def test_it_works_on_a_complicated_union(self, type_cache: strcs.TypeCache):
        provided = Union[Annotated[list[int], "str"], Annotated[int | str | None, '"hello']]
        disassembled = Type.create(provided, expect=types.UnionType, cache=type_cache)
        assert disassembled.original is provided
        assert disassembled.optional is False
        assert disassembled.extracted == provided
        assert not disassembled.is_type_alias
        assert disassembled.origin == type(provided)
        assert disassembled.origin_type == type(provided)

        checkable = disassembled.checkable
        assert (
            checkable == int
            and checkable == list
            and checkable == str
            and isinstance(checkable, InstanceCheckMeta)
        )
        assert disassembled.annotations is None
        assert disassembled.annotated is None
        assert not disassembled.is_annotated
        assert disassembled.without_annotation == provided
        assert disassembled.without_optional == provided
        assert disassembled.nonoptional_union_types == (
            Annotated[int | str | None, '"hello'],
            Annotated[list[int], "str"],
        )
        assert disassembled.fields == []
        assert disassembled.fields_from == provided
        assert disassembled.fields_getter is None
        assert not attrs.has(disassembled.checkable)
        assert not dataclasses.is_dataclass(disassembled.checkable)
        assert disassembled.is_type_for(1)
        assert disassembled.is_type_for("asdf")
        assert disassembled.is_type_for([1, 3])
        assert disassembled.is_type_for(None)
        assert disassembled.is_equivalent_type_for(3)
        assert disassembled.is_equivalent_type_for("asdf")
        assert disassembled.is_equivalent_type_for([1, 2, 3])

        assert (
            disassembled.for_display()
            == 'Annotated[str | int | None, "\\"hello"] | Annotated[list[int], "str"]'
        )

    def test_it_works_on_a_typing_union(self, type_cache: strcs.TypeCache):
        provided = Union[int, str]
        disassembled = Type.create(provided, expect=types.UnionType, cache=type_cache)
        assert disassembled.original is provided
        assert disassembled.optional is False
        assert disassembled.extracted == int | str
        assert not disassembled.is_type_alias
        assert disassembled.origin == type(provided)
        assert disassembled.origin_type == type(provided)
        assert disassembled.checkable == int and isinstance(
            disassembled.checkable, InstanceCheckMeta
        )
        assert disassembled.annotations is None
        assert disassembled.annotated is None
        assert not disassembled.is_annotated
        assert disassembled.without_annotation == int | str
        assert disassembled.without_optional == int | str
        assert disassembled.nonoptional_union_types == (str, int)
        assert disassembled.fields == []
        assert disassembled.fields_from == int | str
        assert disassembled.fields_getter is None
        assert not attrs.has(disassembled.checkable)
        assert not dataclasses.is_dataclass(disassembled.checkable)
        assert disassembled.is_type_for(1)
        assert disassembled.is_type_for("asdf")
        assert not disassembled.is_type_for(None)
        assert disassembled.is_equivalent_type_for(3)
        assert disassembled.is_equivalent_type_for("asdf")

        assert disassembled.for_display() == "str | int"

    def test_it_works_on_an_optional_union(self, type_cache: strcs.TypeCache):
        provided = int | str | None
        disassembled = Type.create(provided, expect=types.UnionType, cache=type_cache)
        assert disassembled.original is provided
        assert disassembled.optional is True
        assert disassembled.extracted == int | str
        assert not disassembled.is_type_alias
        assert disassembled.origin == types.UnionType
        assert disassembled.origin_type == types.UnionType
        assert disassembled.checkable == int and isinstance(
            disassembled.checkable, InstanceCheckMeta
        )
        assert disassembled.annotations is None
        assert disassembled.annotated is None
        assert not disassembled.is_annotated
        assert disassembled.without_annotation == int | str | None
        assert disassembled.without_optional == int | str
        assert disassembled.nonoptional_union_types == (str, int)
        assert disassembled.fields == []
        assert disassembled.fields_from == int | str
        assert disassembled.fields_getter is None
        assert not attrs.has(disassembled.checkable)
        assert not dataclasses.is_dataclass(disassembled.checkable)
        assert disassembled.is_type_for(1)
        assert disassembled.is_type_for("asdf")
        assert disassembled.is_type_for(None)
        assert disassembled.is_equivalent_type_for(3)
        assert disassembled.is_equivalent_type_for("asdf")

        assert disassembled.for_display() == "str | int | None"

    def test_it_works_on_optional_simple_type(self, type_cache: strcs.TypeCache):
        provided = int | None
        disassembled = Type.create(provided, expect=int, cache=type_cache)
        assert disassembled.original is provided
        assert disassembled.optional is True
        assert disassembled.optional_outer is True
        assert disassembled.optional_inner is False
        assert disassembled.extracted == int
        assert not disassembled.is_type_alias
        assert disassembled.origin == int
        assert disassembled.origin_type == int
        assert disassembled.checkable == int and isinstance(
            disassembled.checkable, InstanceCheckMeta
        )
        assert disassembled.annotations is None
        assert not disassembled.is_annotated
        assert disassembled.annotated is None
        assert disassembled.without_annotation == int | None
        assert disassembled.without_optional == int
        assert disassembled.nonoptional_union_types == ()
        assert disassembled.fields == []
        assert disassembled.fields_from == int
        assert disassembled.fields_getter is None
        assert not attrs.has(disassembled.checkable)
        assert not dataclasses.is_dataclass(disassembled.checkable)
        assert disassembled.is_type_for(1)
        assert disassembled.is_type_for(None)
        assert disassembled.is_equivalent_type_for(3)

        assert disassembled.for_display() == "int | None"

    def test_it_works_on_annotated_simple_type(self, type_cache: strcs.TypeCache):
        anno = "hello"
        provided = Annotated[int, anno]
        disassembled = Type.create(provided, expect=int, cache=type_cache)
        assert disassembled.original is provided
        assert disassembled.optional is False
        assert disassembled.extracted == int
        assert not disassembled.is_type_alias
        assert disassembled.origin == int
        assert disassembled.origin_type == int
        assert disassembled.checkable == int and isinstance(
            disassembled.checkable, InstanceCheckMeta
        )
        assert disassembled.annotations == (anno,)
        assert disassembled.is_annotated
        assert disassembled.annotated is provided
        assert disassembled.without_annotation == int
        assert disassembled.without_optional == Annotated[int, anno]
        assert disassembled.nonoptional_union_types == ()
        assert disassembled.fields == []
        assert disassembled.fields_from == int
        assert disassembled.fields_getter is None
        assert not attrs.has(disassembled.checkable)
        assert not dataclasses.is_dataclass(disassembled.checkable)
        assert disassembled.is_type_for(1)
        assert not disassembled.is_type_for(None)
        assert disassembled.is_equivalent_type_for(3)

        assert disassembled.for_display() == 'Annotated[int, "hello"]'

    def test_it_works_on_optional_annotated_simple_type(self, type_cache: strcs.TypeCache):
        anno = "hello"
        provided = Annotated[int | None, anno]
        disassembled = Type.create(provided, expect=int, cache=type_cache)
        assert disassembled.original is provided
        assert disassembled.optional is True
        assert disassembled.optional_outer is False
        assert disassembled.optional_inner is True
        assert disassembled.extracted == int
        assert not disassembled.is_type_alias
        assert disassembled.origin == int
        assert disassembled.origin_type == int
        assert disassembled.checkable == int and isinstance(
            disassembled.checkable, InstanceCheckMeta
        )
        assert disassembled.annotations == (anno,)
        assert disassembled.is_annotated
        assert disassembled.annotated is provided
        assert disassembled.without_annotation == int | None
        assert disassembled.without_optional == Annotated[int, anno]
        assert disassembled.nonoptional_union_types == ()
        assert disassembled.fields == []
        assert disassembled.fields_from == int
        assert disassembled.fields_getter is None
        assert not attrs.has(disassembled.checkable)
        assert not dataclasses.is_dataclass(disassembled.checkable)
        assert disassembled.is_type_for(1)
        assert disassembled.is_type_for(None)
        assert disassembled.is_equivalent_type_for(3)

        assert disassembled.for_display() == 'Annotated[int | None, "hello"]'

    def test_it_works_on_builtin_container_to_simple_type(self, type_cache: strcs.TypeCache):
        provided = list[int]
        disassembled = Type.create(provided, expect=list, cache=type_cache)
        assert disassembled.original is provided
        assert disassembled.optional is False
        assert disassembled.extracted == list[int]
        assert not disassembled.is_type_alias
        assert disassembled.origin == list
        assert disassembled.origin_type == list
        assert disassembled.checkable == list and isinstance(
            disassembled.checkable, InstanceCheckMeta
        )
        assert disassembled.annotations is None
        assert not disassembled.is_annotated
        assert disassembled.annotated is None
        assert disassembled.mro.all_vars == (int,)
        assert disassembled.without_annotation == list[int]
        assert disassembled.without_optional == list[int]
        assert disassembled.nonoptional_union_types == ()
        assert disassembled.fields == []
        assert disassembled.fields_from == list
        assert disassembled.fields_getter is None
        assert not attrs.has(disassembled.checkable)
        assert not dataclasses.is_dataclass(disassembled.checkable)
        assert disassembled.is_type_for([])
        assert not disassembled.is_type_for(None)
        assert disassembled.is_equivalent_type_for([1])

        assert disassembled.for_display() == "list[int]"

    def test_it_works_on_optional_builtin_container_to_simple_type(
        self, type_cache: strcs.TypeCache
    ):
        provided = list[int] | None
        disassembled = Type.create(provided, expect=list, cache=type_cache)
        assert disassembled.original is provided
        assert disassembled.optional is True
        assert disassembled.optional_outer is True
        assert disassembled.optional_inner is False
        assert disassembled.extracted == list[int]
        assert not disassembled.is_type_alias
        assert disassembled.origin == list
        assert disassembled.origin_type == list
        assert disassembled.checkable == list and isinstance(
            disassembled.checkable, InstanceCheckMeta
        )
        assert disassembled.annotations is None
        assert not disassembled.is_annotated
        assert disassembled.annotated is None
        assert disassembled.mro.all_vars == (int,)
        assert disassembled.without_annotation == list[int] | None
        assert disassembled.without_optional == list[int]
        assert disassembled.nonoptional_union_types == ()
        assert disassembled.fields == []
        assert disassembled.fields_from == list
        assert disassembled.fields_getter is None
        assert not attrs.has(disassembled.checkable)
        assert not dataclasses.is_dataclass(disassembled.checkable)
        assert disassembled.is_type_for([])
        assert disassembled.is_type_for(None)
        assert disassembled.is_equivalent_type_for([12])

        assert disassembled.for_display() == "list[int] | None"

    def test_it_works_on_builtin_container_to_multiple_simple_types(
        self, type_cache: strcs.TypeCache
    ):
        provided = dict[str, int]
        disassembled = Type.create(provided, expect=dict, cache=type_cache)
        assert disassembled.original is provided
        assert disassembled.optional is False
        assert disassembled.extracted == dict[str, int]
        assert not disassembled.is_type_alias
        assert disassembled.origin == dict
        assert disassembled.origin_type == dict
        assert disassembled.checkable == dict and isinstance(
            disassembled.checkable, InstanceCheckMeta
        )
        assert disassembled.annotations is None
        assert not disassembled.is_annotated
        assert disassembled.annotated is None
        assert disassembled.mro.all_vars == (str, int)
        assert disassembled.without_annotation == dict[str, int]
        assert disassembled.without_optional == dict[str, int]
        assert disassembled.nonoptional_union_types == ()
        assert disassembled.fields == []
        assert disassembled.fields_from == dict
        assert disassembled.fields_getter is None
        assert not attrs.has(disassembled.checkable)
        assert not dataclasses.is_dataclass(disassembled.checkable)
        assert disassembled.is_type_for({1: 2})
        assert not disassembled.is_type_for(None)
        assert disassembled.is_equivalent_type_for({3: 4})

        assert disassembled.for_display() == "dict[str, int]"

    def test_it_works_on_optional_builtin_container_to_multiple_simple_types(
        self, type_cache: strcs.TypeCache
    ):
        provided = Optional[dict[str, int]]
        disassembled = Type.create(provided, expect=dict, cache=type_cache)
        assert disassembled.original is provided
        assert disassembled.optional is True
        assert disassembled.optional_outer is True
        assert disassembled.optional_inner is False
        assert disassembled.extracted == dict[str, int]
        assert not disassembled.is_type_alias
        assert disassembled.origin == dict
        assert disassembled.origin_type == dict
        assert disassembled.checkable == dict and isinstance(
            disassembled.checkable, InstanceCheckMeta
        )
        assert disassembled.annotations is None
        assert not disassembled.is_annotated
        assert disassembled.annotated is None
        assert disassembled.mro.all_vars == (str, int)
        assert disassembled.without_annotation == dict[str, int] | None
        assert disassembled.without_optional == dict[str, int]
        assert disassembled.nonoptional_union_types == ()
        assert disassembled.fields == []
        assert disassembled.fields_from == dict
        assert disassembled.fields_getter is None
        assert not attrs.has(disassembled.checkable)
        assert not dataclasses.is_dataclass(disassembled.checkable)
        assert disassembled.is_type_for({})
        assert disassembled.is_type_for(None)
        assert disassembled.is_equivalent_type_for({})

        assert disassembled.for_display() == "dict[str, int] | None"

    def test_it_works_on_annotated_optional_builtin_container_to_multiple_simple_types(
        self, type_cache: strcs.TypeCache
    ):
        anno = "stuff"
        provided = Annotated[dict[str, int] | None, anno]
        disassembled = Type.create(provided, expect=dict, cache=type_cache)
        assert disassembled.original is provided
        assert disassembled.optional is True
        assert disassembled.optional_outer is False
        assert disassembled.optional_inner is True
        assert disassembled.extracted == dict[str, int]
        assert not disassembled.is_type_alias
        assert disassembled.origin == dict
        assert disassembled.origin_type == dict
        assert disassembled.checkable == dict and isinstance(
            disassembled.checkable, InstanceCheckMeta
        )
        assert disassembled.annotations == (anno,)
        assert disassembled.is_annotated
        assert disassembled.annotated is provided
        assert disassembled.mro.all_vars == (str, int)
        assert disassembled.without_annotation == dict[str, int] | None
        assert disassembled.without_optional == Annotated[dict[str, int], anno]
        assert disassembled.nonoptional_union_types == ()
        assert disassembled.fields == []
        assert disassembled.fields_from == dict
        assert disassembled.fields_getter is None
        assert not attrs.has(disassembled.checkable)
        assert not dataclasses.is_dataclass(disassembled.checkable)
        assert disassembled.is_type_for({})
        assert disassembled.is_type_for(None)
        assert disassembled.is_equivalent_type_for({})

        assert disassembled.for_display() == 'Annotated[dict[str, int] | None, "stuff"]'

    def test_it_works_on_optional_annotated_builtin_container_to_multiple_simple_types(
        self, type_cache: strcs.TypeCache
    ):
        anno = "stuff"
        provided = Optional[Annotated[dict[str, int], anno]]
        disassembled = Type.create(provided, expect=dict, cache=type_cache)
        assert disassembled.original is provided
        assert disassembled.optional is True
        assert disassembled.optional_outer is True
        assert disassembled.optional_inner is False
        assert disassembled.extracted == dict[str, int]
        assert not disassembled.is_type_alias
        assert disassembled.origin == dict
        assert disassembled.origin_type == dict
        assert disassembled.checkable == dict and isinstance(
            disassembled.checkable, InstanceCheckMeta
        )
        assert disassembled.annotations == (anno,)
        assert disassembled.is_annotated
        assert disassembled.annotated is Annotated[dict[str, int], anno]
        assert disassembled.mro.all_vars == (str, int)
        assert disassembled.without_annotation == dict[str, int] | None
        assert disassembled.without_optional == Annotated[dict[str, int], anno]
        assert disassembled.nonoptional_union_types == ()
        assert disassembled.fields == []
        assert disassembled.fields_from == dict
        assert disassembled.fields_getter is None
        assert not attrs.has(disassembled.checkable)
        assert not dataclasses.is_dataclass(disassembled.checkable)
        assert disassembled.is_type_for({})
        assert disassembled.is_type_for(None)
        assert disassembled.is_equivalent_type_for({})

        assert disassembled.for_display() == 'Annotated[dict[str, int], "stuff"] | None'

    def test_it_works_on_an_attrs_class(self, type_cache: strcs.TypeCache, Dis: Disassembler):
        @attrs.define
        class Thing:
            one: int
            two: str

        provided = Thing
        disassembled = Type.create(provided, expect=Thing, cache=type_cache)
        assert disassembled.original is provided
        assert disassembled.optional is False
        assert disassembled.extracted == Thing
        assert not disassembled.is_type_alias
        assert disassembled.origin == Thing
        assert disassembled.origin_type == Thing
        assert disassembled.checkable == Thing and isinstance(
            disassembled.checkable, InstanceCheckMeta
        )
        assert disassembled.annotations is None
        assert not disassembled.is_annotated
        assert disassembled.annotated is None
        assert disassembled.without_annotation == Thing
        assert disassembled.without_optional == Thing
        assert disassembled.nonoptional_union_types == ()
        assert disassembled.fields == [
            Field(name="one", owner=Thing, disassembled_type=Dis(int)),
            Field(name="two", owner=Thing, disassembled_type=Dis(str)),
        ]
        assert disassembled.fields_from == Thing
        assert disassembled.fields_getter == Partial(fields_from_attrs, type_cache)
        assert attrs.has(disassembled.checkable)
        assert not dataclasses.is_dataclass(disassembled.checkable)
        assert disassembled.is_type_for(Thing(one=1, two="two"))
        assert not disassembled.is_type_for(None)
        assert disassembled.is_equivalent_type_for(Thing(one=1, two="two"))

        @attrs.define
        class Child(Thing):
            pass

        assert disassembled.is_type_for(Child(one=1, two="two"))
        assert disassembled.is_equivalent_type_for(Child(one=1, two="two"))
        assert not Type.create(Child, cache=type_cache).is_equivalent_type_for(
            Thing(one=1, two="two")
        )

        assert disassembled.for_display() == "Thing"

    def test_it_works_on_an_dataclasses_class(
        self, type_cache: strcs.TypeCache, Dis: Disassembler
    ):
        @dataclasses.dataclass
        class Thing:
            one: int
            two: str

        provided = Thing
        disassembled = Type.create(provided, expect=Thing, cache=type_cache)
        assert disassembled.original is provided
        assert disassembled.optional is False
        assert disassembled.extracted == Thing
        assert not disassembled.is_type_alias
        assert disassembled.origin == Thing
        assert disassembled.origin_type == Thing
        assert disassembled.checkable == Thing and isinstance(
            disassembled.checkable, InstanceCheckMeta
        )
        assert disassembled.annotations is None
        assert not disassembled.is_annotated
        assert disassembled.annotated is None
        assert disassembled.without_annotation == Thing
        assert disassembled.without_optional == Thing
        assert disassembled.nonoptional_union_types == ()
        assert disassembled.fields == [
            Field(name="one", owner=Thing, disassembled_type=Dis(int)),
            Field(name="two", owner=Thing, disassembled_type=Dis(str)),
        ]
        assert disassembled.fields_from == Thing
        assert disassembled.fields_getter == Partial(fields_from_dataclasses, type_cache)
        assert not attrs.has(disassembled.checkable)
        assert dataclasses.is_dataclass(disassembled.checkable)
        assert disassembled.is_type_for(Thing(one=1, two="two"))
        assert not disassembled.is_type_for(None)
        assert disassembled.is_equivalent_type_for(Thing(one=1, two="two"))

        @dataclasses.dataclass
        class Child(Thing):
            pass

        assert disassembled.is_type_for(Child(one=1, two="two"))
        assert disassembled.is_equivalent_type_for(Child(one=1, two="two"))
        assert not Type.create(Child, cache=type_cache).is_equivalent_type_for(
            Thing(one=1, two="two")
        )

        assert disassembled.for_display() == "Thing"

    def test_it_works_on_a_normal_class(self, type_cache: strcs.TypeCache, Dis: Disassembler):
        class Thing:
            def __init__(self, one: int, two: str):
                self.one = one
                self.two = two

        provided = Thing
        disassembled = Type.create(provided, expect=Thing, cache=type_cache)
        assert disassembled.original is provided
        assert disassembled.optional is False
        assert disassembled.extracted == Thing
        assert not disassembled.is_type_alias
        assert disassembled.origin == Thing
        assert disassembled.origin_type == Thing
        assert disassembled.checkable == Thing and isinstance(
            disassembled.checkable, InstanceCheckMeta
        )
        assert disassembled.annotations is None
        assert not disassembled.is_annotated
        assert disassembled.annotated is None
        assert disassembled.without_annotation == Thing
        assert disassembled.without_optional == Thing
        assert disassembled.nonoptional_union_types == ()
        assert disassembled.fields == [
            Field(name="one", owner=Thing, disassembled_type=Dis(int)),
            Field(name="two", owner=Thing, disassembled_type=Dis(str)),
        ]
        assert disassembled.fields_from == Thing
        assert disassembled.fields_getter == Partial(fields_from_class, type_cache)
        assert not attrs.has(disassembled.checkable)
        assert not dataclasses.is_dataclass(disassembled.checkable)
        assert disassembled.is_type_for(Thing(one=1, two="two"))
        assert not disassembled.is_type_for(None)
        assert disassembled.is_equivalent_type_for(Thing(one=1, two="two"))

        class Child(Thing):
            pass

        assert disassembled.is_type_for(Child(one=1, two="two"))
        assert disassembled.is_equivalent_type_for(Child(one=1, two="two"))
        assert not Type.create(Child, cache=type_cache).is_equivalent_type_for(
            Thing(one=1, two="two")
        )

        assert disassembled.for_display() == "Thing"

    def test_it_works_on_inherited_generic_container(self, type_cache: strcs.TypeCache):
        class D(dict[str, int]):
            pass

        provided = D
        disassembled = Type.create(provided, expect=D, cache=type_cache)
        assert disassembled.original is provided
        assert disassembled.optional is False
        assert disassembled.extracted == D
        assert not disassembled.is_type_alias
        assert disassembled.origin == D
        assert disassembled.origin_type == D
        assert disassembled.checkable == D and isinstance(
            disassembled.checkable, InstanceCheckMeta
        )
        assert disassembled.annotations is None
        assert not disassembled.is_annotated
        assert disassembled.annotated is None
        assert disassembled.mro.all_vars == (str, int)
        assert disassembled.without_annotation == D
        assert disassembled.without_optional == D
        assert disassembled.nonoptional_union_types == ()
        assert disassembled.fields == []
        assert disassembled.fields_from == D
        assert disassembled.fields_getter == Partial(fields_from_class, type_cache)
        assert not attrs.has(disassembled.checkable)
        assert not dataclasses.is_dataclass(disassembled.checkable)
        assert disassembled.is_type_for(D())
        assert not disassembled.is_type_for(None)
        assert disassembled.is_equivalent_type_for(D())

        assert disassembled.for_display() == "D"

    def test_it_works_on_class_with_complicated_hierarchy(
        self, type_cache: strcs.TypeCache, Dis: Disassembler
    ):
        assert isinstance(T, TypeVar)

        class Thing(Generic[T, U]):
            def __init__(self, one: int, two: str):
                self.one = one
                self.two = two

        class Stuff(Generic[T], Thing[int, T]):
            def __init__(self, one: int, two: str, three: bool):
                super().__init__(one, two)
                self.three = three

        class Blah(Generic[U], Stuff[str]):
            pass

        class Meh(Blah[bool]):
            pass

        class Tree(Meh):
            def __init__(self, four: str):
                super().__init__(1, "two", True)
                self.four = four

        provided = Tree
        disassembled = Type.create(provided, expect=Tree, cache=type_cache)
        assert disassembled.original is provided
        assert disassembled.optional is False
        assert disassembled.extracted == Tree
        assert not disassembled.is_type_alias
        assert disassembled.origin == Tree
        assert disassembled.origin_type == Tree
        assert disassembled.checkable == Tree and isinstance(
            disassembled.checkable, InstanceCheckMeta
        )
        assert disassembled.annotations is None
        assert not disassembled.is_annotated
        assert disassembled.annotated is None
        assert disassembled.mro.typevars == OrderedDict(
            [
                ((Blah, U), bool),
                ((Stuff, T), str),
                ((Thing, T), int),
                (
                    (Thing, U),
                    strcs.MRO.Referal(owner=Stuff, typevar=T, value=str),
                ),
            ]
        )
        assert disassembled.mro.all_vars == (bool, int, str)

        assert disassembled.without_annotation == Tree
        assert disassembled.without_optional == Tree
        assert disassembled.nonoptional_union_types == ()
        assert disassembled.fields == [
            Field(name="one", owner=Meh, original_owner=Thing, disassembled_type=Dis(int)),
            Field(name="two", owner=Meh, original_owner=Thing, disassembled_type=Dis(str)),
            Field(name="three", owner=Meh, original_owner=Stuff, disassembled_type=Dis(bool)),
            Field(name="four", owner=Tree, disassembled_type=Dis(str)),
        ]
        assert disassembled.fields_from == Tree
        assert disassembled.fields_getter == Partial(fields_from_class, type_cache)
        assert not attrs.has(disassembled.checkable)
        assert not dataclasses.is_dataclass(disassembled.checkable)
        assert disassembled.is_type_for(Tree(four="asdf"))
        assert not disassembled.is_type_for(None)
        assert disassembled.is_equivalent_type_for(Tree(four="asdf"))

        assert disassembled.for_display() == "Tree"

    def test_it_works_on_an_annotated_class(self, type_cache: strcs.TypeCache, Dis: Disassembler):
        @attrs.define
        class Thing:
            one: int
            two: str

        anno = "blah"

        provided = Annotated[Thing, anno]
        disassembled = Type.create(provided, expect=Thing, cache=type_cache)
        assert disassembled.original is provided
        assert disassembled.optional is False
        assert disassembled.extracted == Thing
        assert not disassembled.is_type_alias
        assert disassembled.origin == Thing
        assert disassembled.origin_type == Thing
        assert disassembled.checkable == Thing and isinstance(
            disassembled.checkable, InstanceCheckMeta
        )
        assert disassembled.annotations == (anno,)
        assert disassembled.is_annotated
        assert disassembled.annotated is provided
        assert disassembled.without_annotation == Thing
        assert disassembled.without_optional == Annotated[Thing, anno]
        assert disassembled.nonoptional_union_types == ()
        assert disassembled.fields == [
            Field(name="one", owner=Thing, disassembled_type=Dis(int)),
            Field(name="two", owner=Thing, disassembled_type=Dis(str)),
        ]
        assert disassembled.fields_from == Thing
        assert disassembled.fields_getter == Partial(fields_from_attrs, type_cache)
        assert attrs.has(disassembled.checkable)
        assert not dataclasses.is_dataclass(disassembled.checkable)
        assert disassembled.is_type_for(Thing(one=1, two="two"))
        assert not disassembled.is_type_for(None)
        assert disassembled.is_equivalent_type_for(Thing(one=1, two="two"))

        @attrs.define
        class Child(Thing):
            pass

        assert disassembled.is_type_for(Child(one=1, two="two"))
        assert disassembled.is_equivalent_type_for(Child(one=1, two="two"))
        assert not Type.create(Child, cache=type_cache).is_equivalent_type_for(
            Thing(one=1, two="two")
        )

        assert disassembled.for_display() == 'Annotated[Thing, "blah"]'

    def test_it_works_on_an_optional_annotated_class(
        self, type_cache: strcs.TypeCache, Dis: Disassembler
    ):
        @dataclasses.dataclass
        class Thing:
            one: int
            two: str

        anno = "blah"

        provided = Annotated[Thing | None, anno]
        disassembled = Type.create(provided, expect=Thing, cache=type_cache)
        assert disassembled.original is provided
        assert disassembled.optional is True
        assert disassembled.optional_outer is False
        assert disassembled.optional_inner is True
        assert disassembled.extracted == Thing
        assert not disassembled.is_type_alias
        assert disassembled.origin == Thing
        assert disassembled.origin_type == Thing
        assert disassembled.checkable == Thing and isinstance(
            disassembled.checkable, InstanceCheckMeta
        )
        assert disassembled.annotations == (anno,)
        assert disassembled.is_annotated
        assert disassembled.annotated is provided
        assert disassembled.without_annotation == Thing | None
        assert disassembled.without_optional == Annotated[Thing, anno]
        assert disassembled.nonoptional_union_types == ()
        assert disassembled.fields == [
            Field(name="one", owner=Thing, disassembled_type=Dis(int)),
            Field(name="two", owner=Thing, disassembled_type=Dis(str)),
        ]
        assert disassembled.fields_from == Thing
        assert disassembled.fields_getter == Partial(fields_from_dataclasses, type_cache)
        assert not attrs.has(disassembled.checkable)
        assert dataclasses.is_dataclass(disassembled.checkable)
        assert disassembled.is_type_for(Thing(one=1, two="two"))
        assert disassembled.is_type_for(None)
        assert disassembled.is_equivalent_type_for(Thing(one=1, two="two"))

        @dataclasses.dataclass
        class Child(Thing):
            pass

        assert disassembled.is_type_for(Child(one=1, two="two"))
        assert disassembled.is_equivalent_type_for(Child(one=1, two="two"))
        assert not Type.create(Child, cache=type_cache).is_equivalent_type_for(
            Thing(one=1, two="two")
        )

        assert disassembled.for_display() == 'Annotated[Thing | None, "blah"]'

    def test_it_works_on_an_optional_annotated_generic_class(
        self, type_cache: strcs.TypeCache, Dis: Disassembler
    ):
        @dataclasses.dataclass
        class Thing(Generic[T, U]):
            one: T
            two: U

        anno = "blah"

        provided = Annotated[Thing[int, str] | None, anno]
        disassembled = Type.create(provided, expect=Thing, cache=type_cache)
        assert disassembled.original is provided
        assert disassembled.optional is True
        assert disassembled.optional_outer is False
        assert disassembled.optional_inner is True
        assert disassembled.extracted == Thing[int, str]
        assert not disassembled.is_type_alias
        assert disassembled.origin == Thing
        assert disassembled.origin_type == Thing
        assert disassembled.checkable == Thing and isinstance(
            disassembled.checkable, InstanceCheckMeta
        )
        assert disassembled.annotations == (anno,)
        assert disassembled.is_annotated
        assert disassembled.annotated is provided
        assert disassembled.mro.all_vars == (int, str)
        assert disassembled.without_annotation == Thing[int, str] | None
        assert disassembled.without_optional == Annotated[Thing[int, str], anno]
        assert disassembled.nonoptional_union_types == ()
        assert disassembled.fields == [
            Field(name="one", owner=Thing, disassembled_type=Dis(int)),
            Field(name="two", owner=Thing, disassembled_type=Dis(str)),
        ]
        assert disassembled.fields_from == Thing
        assert disassembled.fields_getter == Partial(fields_from_dataclasses, type_cache)
        assert not attrs.has(disassembled.checkable)
        assert dataclasses.is_dataclass(disassembled.checkable)
        assert disassembled.is_type_for(Thing(one=1, two="two"))
        assert disassembled.is_type_for(None)
        assert disassembled.is_equivalent_type_for(Thing(one=1, two="two"))

        @dataclasses.dataclass
        class Child(Thing):
            pass

        assert disassembled.is_type_for(Child(one=1, two="two"))
        assert disassembled.is_equivalent_type_for(Child(one=1, two="two"))
        assert not Type.create(Child, cache=type_cache).is_equivalent_type_for(
            Thing(one=1, two="two")
        )

        assert disassembled.for_display() == 'Annotated[Thing[int, str] | None, "blah"]'

    def test_it_works_on_an_optional_annotated_generic_class_without_concrete_types(
        self, type_cache: strcs.TypeCache, Dis: Disassembler
    ):
        @attrs.define
        class Thing(Generic[T, U]):
            one: T
            two: U

        anno = "blah"

        provided = Annotated[Thing | None, anno]
        disassembled = Type.create(provided, expect=Thing, cache=type_cache)
        assert disassembled.original is provided
        assert disassembled.optional is True
        assert disassembled.optional_outer is False
        assert disassembled.optional_inner is True
        assert disassembled.extracted == Thing
        assert not disassembled.is_type_alias
        assert disassembled.origin == Thing
        assert disassembled.origin_type == Thing
        assert disassembled.checkable == Thing and isinstance(
            disassembled.checkable, InstanceCheckMeta
        )
        assert disassembled.annotations == (anno,)
        assert disassembled.is_annotated
        assert disassembled.annotated is provided
        assert disassembled.mro.all_vars == (strcs.Type.Missing, strcs.Type.Missing)
        assert disassembled.without_annotation == Thing | None
        assert disassembled.without_optional == Annotated[Thing, anno]
        assert disassembled.nonoptional_union_types == ()
        assert disassembled.fields == [
            Field(name="one", owner=Thing, disassembled_type=Dis(object)),
            Field(name="two", owner=Thing, disassembled_type=Dis(object)),
        ]
        assert disassembled.fields_from == Thing
        assert disassembled.fields_getter == Partial(fields_from_attrs, type_cache)
        assert attrs.has(disassembled.checkable)
        assert not dataclasses.is_dataclass(disassembled.checkable)
        assert disassembled.is_type_for(Thing(one=1, two="two"))
        assert disassembled.is_type_for(None)
        assert disassembled.is_equivalent_type_for(Thing(one=1, two="two"))

        @attrs.define
        class Child(Thing):
            pass

        assert disassembled.is_type_for(Child(one=1, two="two"))
        assert disassembled.is_equivalent_type_for(Child(one=1, two="two"))
        assert not Type.create(Child, cache=type_cache).is_equivalent_type_for(
            Thing(one=1, two="two")
        )

        assert disassembled.for_display() == 'Annotated[Thing[~T, ~U] | None, "blah"]'

    def test_it_works_on_an_optional_annotated_generic_class_with_concrete_types(
        self, type_cache: strcs.TypeCache, Dis: Disassembler
    ):
        @attrs.define
        class Thing(Generic[T, U]):
            one: T
            two: U

        anno = "blah"

        provided = Annotated[Thing[int, str] | None, anno]
        disassembled = Type.create(provided, expect=Thing, cache=type_cache)
        assert disassembled.original is provided
        assert disassembled.optional is True
        assert disassembled.optional_outer is False
        assert disassembled.optional_inner is True
        assert disassembled.extracted == Thing[int, str]
        assert not disassembled.is_type_alias
        assert disassembled.origin == Thing
        assert disassembled.origin_type == Thing
        assert disassembled.checkable == Thing and isinstance(
            disassembled.checkable, InstanceCheckMeta
        )
        assert disassembled.annotations == (anno,)
        assert disassembled.is_annotated
        assert disassembled.annotated is provided
        assert disassembled.mro.all_vars == (strcs.Type.Missing, strcs.Type.Missing)
        assert disassembled.without_annotation == Thing[int, str] | None
        assert disassembled.without_optional == Annotated[Thing[int, str], anno]
        assert disassembled.nonoptional_union_types == ()
        assert disassembled.fields == [
            Field(name="one", owner=Thing, disassembled_type=Dis(int)),
            Field(name="two", owner=Thing, disassembled_type=Dis(str)),
        ]
        assert disassembled.fields_from == Thing
        assert disassembled.fields_getter == Partial(fields_from_attrs, type_cache)
        assert attrs.has(disassembled.checkable)
        assert not dataclasses.is_dataclass(disassembled.checkable)
        assert disassembled.is_type_for(Thing(one=1, two="two"))
        assert disassembled.is_type_for(None)
        assert disassembled.is_equivalent_type_for(Thing(one=1, two="two"))

        @attrs.define
        class Child(Thing):
            pass

        assert disassembled.is_type_for(Child(one=1, two="two"))
        assert disassembled.is_equivalent_type_for(Child(one=1, two="two"))
        assert not Type.create(Child, cache=type_cache).is_equivalent_type_for(
            Thing(one=1, two="two")
        )

        assert disassembled.for_display() == 'Annotated[Thing[int, str] | None, "blah"]'

    def test_it_doesnt_confuse_int_and_boolean(
        self, Dis: Disassembler, type_cache: strcs.TypeCache
    ):
        def clear() -> None:
            type_cache.clear()

        for provided, origin in (
            (True, bool),
            (1, int),
            (clear, None),
            (1, int),
            (True, bool),
            (clear, None),
            (False, bool),
            (0, int),
            (clear, None),
            (0, int),
            (False, bool),
            (clear, None),
            (True, bool),
            (1, int),
        ):
            if provided is clear:
                clear()
                continue

            disassembled = Type.create(provided, expect=bool, cache=type_cache)
            assert disassembled.original is provided
            assert disassembled.optional is False
            assert disassembled.extracted is provided
            assert not disassembled.is_type_alias
            assert disassembled.origin == origin
            assert disassembled.origin_type == origin

            checkable = disassembled.checkable
            assert checkable.Meta.original is provided
            assert checkable.Meta.typ is origin

            assert disassembled.checkable == origin and isinstance(
                disassembled.checkable, InstanceCheckMeta
            )
            assert disassembled.annotations is None
            assert disassembled.annotated is None
            assert not disassembled.is_annotated
            assert disassembled.without_annotation is provided
            assert disassembled.without_optional is provided
            assert disassembled.nonoptional_union_types == ()
            assert disassembled.fields == []
            assert disassembled.fields_from is origin
            assert disassembled.fields_getter is None
            assert not attrs.has(disassembled.checkable)
            assert not dataclasses.is_dataclass(disassembled.checkable)
            assert not disassembled.is_type_for(1)
            assert not disassembled.is_type_for(True)
            assert not disassembled.is_type_for(None)
            assert not disassembled.is_equivalent_type_for(bool)

    def test_it_works_with_primitive_NewType(self, type_cache: strcs.TypeCache, Dis: Disassembler):
        MyInt = NewType("MyInt", int)
        MyIntSuper = NewType("MyIntSuper", MyInt)
        MyStr = NewType("MyStr", str)
        MyOtherInt = NewType("MyOtherInt", int)

        provided = MyInt
        disassembled = Type.create(provided, expect=MyInt, cache=type_cache)
        assert disassembled.original is provided
        assert disassembled.optional is False
        assert disassembled.optional_outer is False
        assert disassembled.optional_inner is False
        assert disassembled.extracted == int
        assert disassembled.is_type_alias
        assert disassembled.origin == MyInt
        assert disassembled.origin_type == int

        assert disassembled.checkable == MyInt
        assert disassembled.checkable != MyOtherInt
        assert disassembled.checkable == int
        assert isinstance(disassembled.checkable, InstanceCheckMeta)

        assert issubclass(int, disassembled.checkable)
        assert issubclass(Type.create(MyInt, cache=type_cache).checkable, disassembled.checkable)
        other = Type.create(MyOtherInt, cache=type_cache).checkable
        this = disassembled.checkable
        mystr = Type.create(MyStr, cache=type_cache).checkable
        spr = Type.create(MyIntSuper, cache=type_cache).checkable
        assert issubclass(this, spr)
        assert not issubclass(spr, this)
        assert not issubclass(other, this)
        assert not issubclass(this, other)
        assert not issubclass(mystr, this)
        assert not issubclass(this, mystr)
        assert disassembled.is_equivalent_type_for(1)
        assert disassembled.is_equivalent_type_for(int)
        assert disassembled.is_equivalent_type_for(MyInt)
        assert not disassembled.is_equivalent_type_for(MyOtherInt)

        assert disassembled.annotations is None
        assert not disassembled.is_annotated
        assert disassembled.annotated is None
        assert disassembled.mro.all_vars == ()
        assert disassembled.without_annotation == MyInt
        assert disassembled.without_optional == MyInt
        assert disassembled.nonoptional_union_types == ()
        assert disassembled.fields == []
        assert disassembled.fields_from is MyInt
        assert disassembled.fields_getter is None
        assert not attrs.has(disassembled.checkable)
        assert not dataclasses.is_dataclass(disassembled.checkable)
        assert not disassembled.is_type_for(type)
        assert not disassembled.is_type_for(MyInt)
        assert not disassembled.is_type_for(int)
        assert not disassembled.is_type_for(str)
        assert not disassembled.is_type_for(MyOtherInt)
        assert disassembled.is_equivalent_type_for(34)

        assert disassembled.for_display() == "MyInt"

    def test_it_works_with_wrapped_NewType(self, type_cache: strcs.TypeCache, Dis: Disassembler):
        MyInt = NewType("MyInt", int)
        MyOtherInt = NewType("MyOtherInt", int)

        provided = Annotated[MyInt | None, "asdf"] | None
        disassembled = Type.create(provided, expect=MyInt, cache=type_cache)
        assert disassembled.original is provided
        assert disassembled.optional is True
        assert disassembled.optional_outer is True
        assert disassembled.optional_inner is True
        assert disassembled.extracted == int
        assert disassembled.is_type_alias
        assert disassembled.origin == MyInt
        assert disassembled.origin_type == int

        assert disassembled.checkable == MyInt
        assert disassembled.checkable != MyOtherInt
        assert disassembled.checkable == int
        assert isinstance(disassembled.checkable, InstanceCheckMeta)

        assert disassembled.annotations == ("asdf",)
        assert disassembled.is_annotated
        assert disassembled.annotated == Annotated[MyInt | None, "asdf"]
        assert disassembled.mro.all_vars == ()
        assert disassembled.without_annotation == MyInt | None
        assert disassembled.without_optional == Annotated[MyInt, "asdf"]
        assert disassembled.nonoptional_union_types == ()
        assert disassembled.fields == []
        assert disassembled.fields_from is MyInt
        assert disassembled.fields_getter is None
        assert not attrs.has(disassembled.checkable)
        assert not dataclasses.is_dataclass(disassembled.checkable)
        assert not disassembled.is_type_for(type)
        assert not disassembled.is_type_for(MyInt)
        assert not disassembled.is_type_for(int)
        assert not disassembled.is_type_for(str)
        assert not disassembled.is_type_for(MyOtherInt)
        assert disassembled.is_equivalent_type_for(34)

        assert disassembled.for_display() == 'Annotated[MyInt | None, "asdf"] | None'


class TestGettingFields:
    def test_it_works_when_there_is_a_chain(self, type_cache: strcs.TypeCache, Dis: Disassembler):
        @attrs.define
        class Stuff:
            thing: "Thing"

        @attrs.define
        class Thing:
            stuff: Optional["Stuff"]

        resolve_types(Thing, globals(), locals(), type_cache=type_cache)

        disassembled = Dis(Thing)
        assert disassembled.fields == [
            Field(name="stuff", owner=Thing, disassembled_type=Dis(Stuff | None))
        ]

    def test_it_works_on_normal_class(self, type_cache: strcs.TypeCache, Dis: Disassembler):
        class Thing:
            def __init__(self, one: int, /, two: str, *, three: bool = False, **kwargs):
                pass

        disassembled = Dis(Thing)
        assert disassembled.fields_getter == Partial(fields_from_class, type_cache)
        assert disassembled.fields_from is Thing
        assertParams(
            disassembled.fields,
            [
                Field(
                    name="one",
                    owner=Thing,
                    kind=inspect.Parameter.POSITIONAL_ONLY,
                    disassembled_type=Dis(int),
                ),
                Field(
                    name="two",
                    owner=Thing,
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    disassembled_type=Dis(str),
                ),
                Field(
                    name="three",
                    owner=Thing,
                    kind=inspect.Parameter.KEYWORD_ONLY,
                    disassembled_type=Dis(bool),
                    default=Default(False),
                ),
                Field(
                    name="",
                    owner=Thing,
                    kind=inspect.Parameter.VAR_KEYWORD,
                    disassembled_type=Dis(object),
                ),
            ],
        )

    def test_it_works_on_attrs_class(self, type_cache: strcs.TypeCache, Dis: Disassembler):
        @attrs.define
        class Thing:
            one: int
            two: str = "one"
            three: bool = attrs.field(kw_only=True, default=False)

        disassembled = Dis(Thing)
        assert disassembled.fields_getter == Partial(fields_from_attrs, type_cache)
        assert disassembled.fields_from is Thing
        assertParams(
            disassembled.fields,
            [
                Field(
                    name="one",
                    owner=Thing,
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    disassembled_type=Dis(int),
                ),
                Field(
                    name="two",
                    owner=Thing,
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    disassembled_type=Dis(str),
                    default=Default("one"),
                ),
                Field(
                    name="three",
                    kind=inspect.Parameter.KEYWORD_ONLY,
                    owner=Thing,
                    disassembled_type=Dis(bool),
                    default=Default(False),
                ),
            ],
        )

    def test_it_works_on_dataclasses_class(self, type_cache: strcs.TypeCache, Dis: Disassembler):
        @dataclasses.dataclass
        class Thing:
            one: int
            two: str = "one"
            three: bool = dataclasses.field(kw_only=True, default=False)

        disassembled = Dis(Thing)
        assert disassembled.fields_getter == Partial(fields_from_dataclasses, type_cache)
        assert disassembled.fields_from is Thing
        assertParams(
            disassembled.fields,
            [
                Field(
                    name="one",
                    owner=Thing,
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    disassembled_type=Dis(int),
                ),
                Field(
                    owner=Thing,
                    name="two",
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    disassembled_type=Dis(str),
                    default=Default("one"),
                ),
                Field(
                    name="three",
                    owner=Thing,
                    kind=inspect.Parameter.KEYWORD_ONLY,
                    disassembled_type=Dis(bool),
                    default=Default(False),
                ),
            ],
        )


class TestAnnotations:
    def test_it_can_return_no_annotation(self, Dis: Disassembler):
        assert Dis(int).ann is None
        assert Dis(int | None).ann is None
        assert Dis(int | str).ann is None
        assert Dis(int | str | None).ann is None
        assert Dis(list[int]).ann is None
        assert Dis(list[int] | None).ann is None

        class Thing:
            pass

        assert Dis(Thing).ann is None

    def test_it_can_return_an_annotation_with_new_creator(self, Dis: Disassembler):
        def creator(value: object, /, _meta: strcs.Meta): ...

        ann = Dis(Annotated[int, creator]).ann
        assert isinstance(ann, strcs.Ann)
        assert ann.creator is creator

    def test_it_can_return_an_annotation_with_new_adjustable_meta(
        self, type_cache: strcs.TypeCache, Dis: Disassembler
    ):
        class AdjustMeta:
            @classmethod
            def adjusted_meta(
                cls, meta: strcs.Meta, typ: strcs.Type, type_cache: strcs.TypeCache
            ) -> strcs.Meta:
                return meta.clone({"one": 1})

        adjustment = AdjustMeta()
        ann = Dis(Annotated[int, adjustment]).ann
        assert ann is adjustment
        assert strcs.is_adjustable_meta(ann)

        meta = strcs.Meta({"two": 2})
        m = ann.adjusted_meta(meta, Dis(int), type_cache)
        assert m.data == {"one": 1, "two": 2}
        assert meta.data == {"two": 2}

    def test_it_can_return_an_annotation_with_new_MetaAnnotation(
        self, type_cache: strcs.TypeCache, Dis: Disassembler
    ):
        @attrs.define
        class Info(strcs.MetaAnnotation):
            three: str

        info = Info(three="three")
        ann = Dis(Annotated[int, info]).ann
        assert isinstance(ann, strcs.Ann), ann
        assert ann.creator is None
        assert ann.meta is info

        meta = strcs.Meta({"two": 2})
        m = ann.adjusted_meta(meta, Dis(int), type_cache)
        assert m.data == {"__call_defined_annotation__": info, "two": 2}
        assert meta.data == {"two": 2}

    def test_it_can_return_an_annotation_with_new_MergedMetaAnnotation(
        self, type_cache: strcs.TypeCache, Dis: Disassembler
    ):
        @attrs.define
        class Info(strcs.MergedMetaAnnotation):
            three: str

        info = Info(three="three")
        ann = Dis(Annotated[int, info]).ann
        assert isinstance(ann, strcs.Ann), ann
        assert ann.creator is None
        assert ann.meta is info

        meta = strcs.Meta({"two": 2})
        m = ann.adjusted_meta(meta, Dis(int), type_cache)
        assert m.data == {"three": "three", "two": 2}
        assert meta.data == {"two": 2}

    def test_it_can_return_an_annotation_with_new_Ann(
        self, type_cache: strcs.TypeCache, Dis: Disassembler
    ):
        def creator1(args: strcs.CreateArgs[int]) -> int:
            return 2

        def creator2(value: object) -> strcs.ConvertResponse[int]: ...

        class A(strcs.Ann[int]):
            def adjusted_meta(
                self, meta: strcs.Meta, typ: strcs.Type[int], type_cache: strcs.TypeCache
            ) -> strcs.Meta:
                return meta.clone({"one": 1})

        a = A(creator=creator2)
        ann = Dis(Annotated[int, a]).ann
        assert isinstance(ann, strcs.Ann), ann
        assert ann is a

        meta = strcs.Meta({"two": 2})
        m = ann.adjusted_meta(meta, Dis(int), type_cache)
        assert m.data == {"one": 1, "two": 2}
        assert meta.data == {"two": 2}

        reg = strcs.CreateRegister()
        assert ann.adjusted_creator(creator1, reg, Dis(int), type_cache) == creator2


class TestEquality:
    def test_it_matches_any_Type_against_TypeMissing(self, Dis: Disassembler):
        typ = Dis(int)
        assert typ == strcs.Type.Missing

        typ2 = Dis(Annotated[None, 1])
        assert typ2 == strcs.Type.Missing

        class Thing:
            pass

        typ3 = Dis(Thing | None)
        assert typ3 == strcs.Type.Missing

    def test_it_matches_against_checkable_instances_and_original_type(self, Dis: Disassembler):
        typ = Dis(int)
        assert typ == int
        assert typ == typ.checkable

        typ2 = Dis(int)
        assert typ2 == int
        assert typ2 == typ.checkable

        class Thing:
            pass

        typ3 = Dis(Annotated[Thing, 1])
        assert typ3 == Thing
        assert typ3 == typ3.checkable
        assert typ3 != typ2.checkable
        assert typ2 != typ3.checkable

    def test_it_matches_against_optionals(self, Dis: Disassembler):
        typ = Dis(int)
        nun = None
        assert typ != nun
        assert typ == int
        assert typ == typ.checkable

        typ2 = Dis(int | None)
        assert typ2 == nun
        assert typ2 == int
        assert typ2 == typ.checkable

        class Thing:
            pass

        typ3 = Dis(Annotated[Thing | None, 1])
        assert typ3 == Thing
        assert typ3 == nun
        assert typ3 == typ3.checkable
        assert typ3 != typ2.checkable
        assert typ2 != typ3.checkable

    def test_it_matches_against_unions_and_partial_unions(self, Dis: Disassembler):
        typ = Dis(int)
        nun = None
        assert typ != nun
        assert typ == int
        assert typ != str
        assert typ == typ.checkable

        typ2 = Dis(int | bool | str | None)
        assert typ2 == nun
        assert typ2 == int
        assert typ2 == str
        assert typ2 == int | str
        assert typ2 == bool | str
        assert typ2 == int | None
        assert typ2 == typ.checkable

        class Thing:
            pass

        typ3 = Dis(Annotated[Thing | bool | None, 1])
        assert typ3 == Thing
        assert typ3 == nun
        assert typ3 != str
        assert typ3 == bool
        assert typ3 == typ3.checkable
        # Typ2 has things not in this union
        assert typ3 != typ2.checkable
        assert typ2 != typ3.checkable


class TestFindingProvidedSubtype:
    def test_it_can_find_the_provided_subtype(self, Dis: Disassembler):
        class Item:
            pass

        class ItemA(Item):
            pass

        class ItemB(Item):
            pass

        class ItemC(Item):
            pass

        I = TypeVar("I", bound=Item)

        class Container(Generic[I]):
            pass

        container_a = Dis(Container[ItemA])
        container_b = Dis(Container[ItemB])
        container_c = Dis(Container[ItemC])

        assert container_a.find_generic_subtype(Item) == (ItemA,)
        assert container_b.find_generic_subtype(Item) == (ItemB,)
        assert container_c.find_generic_subtype(Item) == (ItemC,)

    def test_it_can_find_multiple_subtypes(self, Dis: Disassembler):
        class One:
            pass

        class Two:
            pass

        class OneA(One):
            pass

        class OneB(One):
            pass

        class TwoA(Two):
            pass

        class TwoB(Two):
            pass

        O = TypeVar("O", bound=One)
        T = TypeVar("T", bound=Two)

        class Container(Generic[O, T]):
            pass

        container_a = Dis(Container[OneA, TwoB])
        container_b = Dis(Container[OneB, TwoB])

        assert container_a.find_generic_subtype(One, Two) == (OneA, TwoB)
        assert container_b.find_generic_subtype(One, Two) == (OneB, TwoB)

    def test_it_can_find_a_partial_number_of_subtypes(self, Dis: Disassembler):
        class One:
            pass

        class Two:
            pass

        class OneA(One):
            pass

        class OneB(One):
            pass

        class TwoA(Two):
            pass

        class TwoB(Two):
            pass

        O = TypeVar("O", bound=One)
        T = TypeVar("T", bound=Two)

        class Container(Generic[O, T]):
            pass

        container_a = Dis(Container[OneA, TwoA])
        assert container_a.find_generic_subtype(One) == (OneA,)

    def test_it_complains_if_want_too_many_types(self, Dis: Disassembler):
        class One:
            pass

        class Two:
            pass

        class OneA(One):
            pass

        class OneB(One):
            pass

        O = TypeVar("O", bound=One)

        class Container(Generic[O]):
            pass

        container_a = Dis(Container[OneA])
        with pytest.raises(
            ValueError, match=re.escape("The type has less typevars (1) than wanted (2)")
        ):
            container_a.find_generic_subtype(One, Two)

    def test_it_complains_if_want_wrong_subtype(self, Dis: Disassembler):
        class One:
            pass

        class Two:
            pass

        class OneA(One):
            pass

        class OneB(One):
            pass

        O = TypeVar("O", bound=One)

        class Container(Generic[O]):
            pass

        container_a = Dis(Container[OneA])
        with pytest.raises(
            ValueError,
            match="The concrete type <class '[^']+'> is not a subclass of what was asked for <class '[^']+'>",
        ):
            container_a.find_generic_subtype(Two)
