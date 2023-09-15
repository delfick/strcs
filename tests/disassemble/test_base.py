# coding: spec
import dataclasses
import inspect
import re
import types
import typing as tp
from collections import OrderedDict
from dataclasses import dataclass, is_dataclass
from functools import partial

import attrs
import pytest
from attrs import define
from attrs import has as attrs_has

import strcs
from strcs import Field, InstanceCheckMeta, Type, resolve_types
from strcs.disassemble.base import (
    fields_from_attrs,
    fields_from_class,
    fields_from_dataclasses,
)
from strcs.disassemble.fields import Default

from .test_helpers import assertParams


@pytest.fixture()
def type_cache() -> strcs.TypeCache:
    return strcs.TypeCache()


class Disassembler:
    def __init__(self, type_cache: strcs.TypeCache):
        self.type_cache = type_cache

    def __call__(self, typ: object) -> strcs.Type:
        return Type.create(typ, cache=self.type_cache)


@pytest.fixture()
def Dis(type_cache: strcs.TypeCache) -> Disassembler:
    return Disassembler(type_cache)


class Partial:
    got: object
    equals: bool

    def __init__(self, func: tp.Callable, *args: object):
        self.func = func
        self.args = args

    def __eq__(self, got: object) -> bool:
        self.got = got
        self.equals = False

        if not isinstance(self.got, partial):
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


T = tp.TypeVar("T")
U = tp.TypeVar("U")

describe "Type":
    it "works on None", type_cache: strcs.TypeCache:
        provided = None
        disassembled = Type.create(provided, expect=type(None), cache=type_cache)
        assert disassembled.original is provided
        assert disassembled.optional is False
        assert disassembled.extracted is None
        assert disassembled.origin == type(None)
        nun = None
        assert disassembled.checkable == nun and isinstance(
            disassembled.checkable, InstanceCheckMeta
        )
        assert disassembled.annotation is None
        assert disassembled.annotated is None
        assert not disassembled.is_annotated
        assert disassembled.without_annotation is None
        assert disassembled.without_optional is None
        assert disassembled.nonoptional_union_types == ()
        assert disassembled.fields == []
        assert disassembled.fields_from == type(None)
        assert disassembled.fields_getter is None
        assert not attrs_has(disassembled.checkable)
        assert not is_dataclass(disassembled.checkable)
        assert disassembled.is_type_for(None)
        assert not disassembled.is_type_for(1)
        assert disassembled.is_equivalent_type_for(None)

        assert disassembled.for_display() == "None"

    it "doesn't overcome python limitations with annotating None and thinks we annotated type of None", type_cache: strcs.TypeCache:
        provided = tp.Annotated[None, 1]
        disassembled = Type.create(provided, expect=type(None), cache=type_cache)
        assert disassembled.original is provided
        assert disassembled.optional is False
        assert disassembled.extracted == type(None)
        assert disassembled.origin == type(None)
        assert disassembled.checkable == type(None) and isinstance(
            disassembled.checkable, InstanceCheckMeta
        )
        assert disassembled.annotation == 1
        assert disassembled.annotated is provided
        assert disassembled.is_annotated
        assert disassembled.without_annotation == type(None)
        assert disassembled.without_optional == provided
        assert disassembled.nonoptional_union_types == ()
        assert disassembled.fields == []
        assert disassembled.fields_from == type(None)
        assert disassembled.fields_getter == Partial(fields_from_class, type_cache)
        assert not attrs_has(disassembled.checkable)
        assert not is_dataclass(disassembled.checkable)
        assert disassembled.is_type_for(None)
        assert not disassembled.is_type_for(1)
        assert disassembled.is_equivalent_type_for(None)

        assert disassembled.for_display() == "Annotated[NoneType, 1]"

    it "works on simple type", type_cache: strcs.TypeCache:
        provided = int
        disassembled = Type.create(provided, expect=int, cache=type_cache)
        assert disassembled.original is provided
        assert disassembled.optional is False
        assert disassembled.extracted == int
        assert disassembled.origin == int
        assert disassembled.checkable == int and isinstance(
            disassembled.checkable, InstanceCheckMeta
        )
        assert disassembled.annotation is None
        assert disassembled.annotated is None
        assert not disassembled.is_annotated
        assert disassembled.without_annotation == int
        assert disassembled.without_optional == int
        assert disassembled.nonoptional_union_types == ()
        assert disassembled.fields == []
        assert disassembled.fields_from == int
        assert disassembled.fields_getter is None
        assert not attrs_has(disassembled.checkable)
        assert not is_dataclass(disassembled.checkable)
        assert disassembled.is_type_for(1)
        assert not disassembled.is_type_for(None)
        assert disassembled.is_equivalent_type_for(3)

        assert disassembled.for_display() == "int"

    it "works on a union", type_cache: strcs.TypeCache:
        provided = int | str
        disassembled = Type.create(provided, expect=types.UnionType, cache=type_cache)
        assert disassembled.original is provided
        assert disassembled.optional is False
        assert disassembled.extracted == int | str
        assert disassembled.origin == types.UnionType
        assert disassembled.checkable == int and isinstance(
            disassembled.checkable, InstanceCheckMeta
        )
        assert disassembled.annotation is None
        assert disassembled.annotated is None
        assert disassembled.mro.all_vars == ()
        assert not disassembled.is_annotated
        assert disassembled.without_annotation == int | str
        assert disassembled.without_optional == int | str
        assert disassembled.nonoptional_union_types == (str, int)
        assert disassembled.fields == []
        assert disassembled.fields_from == int | str
        assert disassembled.fields_getter is None
        assert not attrs_has(disassembled.checkable)
        assert not is_dataclass(disassembled.checkable)
        assert disassembled.is_type_for(1)
        assert disassembled.is_type_for("asdf")
        assert not disassembled.is_type_for(None)
        assert disassembled.is_equivalent_type_for(3)
        assert disassembled.is_equivalent_type_for("asdf")

        assert disassembled.for_display() == "str | int"

    it "works on a complicated union", type_cache: strcs.TypeCache:
        provided = tp.Union[
            tp.Annotated[list[int], "str"], tp.Annotated[int | str | None, '"hello']
        ]
        disassembled = Type.create(provided, expect=types.UnionType, cache=type_cache)
        assert disassembled.original is provided
        assert disassembled.optional is False
        assert disassembled.extracted == provided
        assert disassembled.origin == type(provided)

        checkable = disassembled.checkable
        assert (
            checkable == int
            and checkable == list
            and checkable == str
            and isinstance(checkable, InstanceCheckMeta)
        )
        assert disassembled.annotation is None
        assert disassembled.annotated is None
        assert not disassembled.is_annotated
        assert disassembled.without_annotation == provided
        assert disassembled.without_optional == provided
        assert disassembled.nonoptional_union_types == (
            tp.Annotated[int | str | None, '"hello'],
            tp.Annotated[list[int], "str"],
        )
        assert disassembled.fields == []
        assert disassembled.fields_from == provided
        assert disassembled.fields_getter is None
        assert not attrs_has(disassembled.checkable)
        assert not is_dataclass(disassembled.checkable)
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

    it "works on a typing union", type_cache: strcs.TypeCache:
        provided = tp.Union[int, str]
        disassembled = Type.create(provided, expect=types.UnionType, cache=type_cache)
        assert disassembled.original is provided
        assert disassembled.optional is False
        assert disassembled.extracted == int | str
        assert disassembled.origin == type(provided)
        assert disassembled.checkable == int and isinstance(
            disassembled.checkable, InstanceCheckMeta
        )
        assert disassembled.annotation is None
        assert disassembled.annotated is None
        assert not disassembled.is_annotated
        assert disassembled.without_annotation == int | str
        assert disassembled.without_optional == int | str
        assert disassembled.nonoptional_union_types == (str, int)
        assert disassembled.fields == []
        assert disassembled.fields_from == int | str
        assert disassembled.fields_getter is None
        assert not attrs_has(disassembled.checkable)
        assert not is_dataclass(disassembled.checkable)
        assert disassembled.is_type_for(1)
        assert disassembled.is_type_for("asdf")
        assert not disassembled.is_type_for(None)
        assert disassembled.is_equivalent_type_for(3)
        assert disassembled.is_equivalent_type_for("asdf")

        assert disassembled.for_display() == "str | int"

    it "works on an optional union", type_cache: strcs.TypeCache:
        provided = int | str | None
        disassembled = Type.create(provided, expect=types.UnionType, cache=type_cache)
        assert disassembled.original is provided
        assert disassembled.optional is True
        assert disassembled.extracted == int | str
        assert disassembled.origin == types.UnionType
        assert disassembled.checkable == int and isinstance(
            disassembled.checkable, InstanceCheckMeta
        )
        assert disassembled.annotation is None
        assert disassembled.annotated is None
        assert not disassembled.is_annotated
        assert disassembled.without_annotation == int | str | None
        assert disassembled.without_optional == int | str
        assert disassembled.nonoptional_union_types == (str, int)
        assert disassembled.fields == []
        assert disassembled.fields_from == int | str
        assert disassembled.fields_getter is None
        assert not attrs_has(disassembled.checkable)
        assert not is_dataclass(disassembled.checkable)
        assert disassembled.is_type_for(1)
        assert disassembled.is_type_for("asdf")
        assert disassembled.is_type_for(None)
        assert disassembled.is_equivalent_type_for(3)
        assert disassembled.is_equivalent_type_for("asdf")

        assert disassembled.for_display() == "str | int | None"

    it "works on optional simple type", type_cache: strcs.TypeCache:
        provided = int | None
        disassembled = Type.create(provided, expect=int, cache=type_cache)
        assert disassembled.original is provided
        assert disassembled.optional is True
        assert disassembled.optional_outer is True
        assert disassembled.optional_inner is False
        assert disassembled.extracted == int
        assert disassembled.origin == int
        assert disassembled.checkable == int and isinstance(
            disassembled.checkable, InstanceCheckMeta
        )
        assert disassembled.annotation is None
        assert not disassembled.is_annotated
        assert disassembled.annotated is None
        assert disassembled.without_annotation == int | None
        assert disassembled.without_optional == int
        assert disassembled.nonoptional_union_types == ()
        assert disassembled.fields == []
        assert disassembled.fields_from == int
        assert disassembled.fields_getter is None
        assert not attrs_has(disassembled.checkable)
        assert not is_dataclass(disassembled.checkable)
        assert disassembled.is_type_for(1)
        assert disassembled.is_type_for(None)
        assert disassembled.is_equivalent_type_for(3)

        assert disassembled.for_display() == "int | None"

    it "works on annotated simple type", type_cache: strcs.TypeCache:
        anno = "hello"
        provided = tp.Annotated[int, anno]
        disassembled = Type.create(provided, expect=int, cache=type_cache)
        assert disassembled.original is provided
        assert disassembled.optional is False
        assert disassembled.extracted == int
        assert disassembled.origin == int
        assert disassembled.checkable == int and isinstance(
            disassembled.checkable, InstanceCheckMeta
        )
        assert disassembled.annotation is anno
        assert disassembled.is_annotated
        assert disassembled.annotated is provided
        assert disassembled.without_annotation == int
        assert disassembled.without_optional == tp.Annotated[int, anno]
        assert disassembled.nonoptional_union_types == ()
        assert disassembled.fields == []
        assert disassembled.fields_from == int
        assert disassembled.fields_getter is None
        assert not attrs_has(disassembled.checkable)
        assert not is_dataclass(disassembled.checkable)
        assert disassembled.is_type_for(1)
        assert not disassembled.is_type_for(None)
        assert disassembled.is_equivalent_type_for(3)

        assert disassembled.for_display() == 'Annotated[int, "hello"]'

    it "works on optional annotated simple type", type_cache: strcs.TypeCache:
        anno = "hello"
        provided = tp.Annotated[tp.Optional[int], anno]
        disassembled = Type.create(provided, expect=int, cache=type_cache)
        assert disassembled.original is provided
        assert disassembled.optional is True
        assert disassembled.optional_outer is False
        assert disassembled.optional_inner is True
        assert disassembled.extracted == int
        assert disassembled.origin == int
        assert disassembled.checkable == int and isinstance(
            disassembled.checkable, InstanceCheckMeta
        )
        assert disassembled.annotation is anno
        assert disassembled.is_annotated
        assert disassembled.annotated is provided
        assert disassembled.without_annotation == int | None
        assert disassembled.without_optional == tp.Annotated[int, anno]
        assert disassembled.nonoptional_union_types == ()
        assert disassembled.fields == []
        assert disassembled.fields_from == int
        assert disassembled.fields_getter is None
        assert not attrs_has(disassembled.checkable)
        assert not is_dataclass(disassembled.checkable)
        assert disassembled.is_type_for(1)
        assert disassembled.is_type_for(None)
        assert disassembled.is_equivalent_type_for(3)

        assert disassembled.for_display() == 'Annotated[int | None, "hello"]'

    it "works on builtin container to simple type", type_cache: strcs.TypeCache:
        provided = list[int]
        disassembled = Type.create(provided, expect=list, cache=type_cache)
        assert disassembled.original is provided
        assert disassembled.optional is False
        assert disassembled.extracted == list[int]
        assert disassembled.origin == list
        assert disassembled.checkable == list and isinstance(
            disassembled.checkable, InstanceCheckMeta
        )
        assert disassembled.annotation is None
        assert not disassembled.is_annotated
        assert disassembled.annotated is None
        assert disassembled.mro.all_vars == (int,)
        assert disassembled.without_annotation == list[int]
        assert disassembled.without_optional == list[int]
        assert disassembled.nonoptional_union_types == ()
        assert disassembled.fields == []
        assert disassembled.fields_from == list
        assert disassembled.fields_getter is None
        assert not attrs_has(disassembled.checkable)
        assert not is_dataclass(disassembled.checkable)
        assert disassembled.is_type_for([])
        assert not disassembled.is_type_for(None)
        assert disassembled.is_equivalent_type_for([1])

        assert disassembled.for_display() == "list[int]"

    it "works on optional builtin container to simple type", type_cache: strcs.TypeCache:
        provided = list[int] | None
        disassembled = Type.create(provided, expect=list, cache=type_cache)
        assert disassembled.original is provided
        assert disassembled.optional is True
        assert disassembled.optional_outer is True
        assert disassembled.optional_inner is False
        assert disassembled.extracted == list[int]
        assert disassembled.origin == list
        assert disassembled.checkable == list and isinstance(
            disassembled.checkable, InstanceCheckMeta
        )
        assert disassembled.annotation is None
        assert not disassembled.is_annotated
        assert disassembled.annotated is None
        assert disassembled.mro.all_vars == (int,)
        assert disassembled.without_annotation == list[int] | None
        assert disassembled.without_optional == list[int]
        assert disassembled.nonoptional_union_types == ()
        assert disassembled.fields == []
        assert disassembled.fields_from == list
        assert disassembled.fields_getter is None
        assert not attrs_has(disassembled.checkable)
        assert not is_dataclass(disassembled.checkable)
        assert disassembled.is_type_for([])
        assert disassembled.is_type_for(None)
        assert disassembled.is_equivalent_type_for([12])

        assert disassembled.for_display() == "list[int] | None"

    it "works on builtin container to multiple simple types", type_cache: strcs.TypeCache:
        provided = dict[str, int]
        disassembled = Type.create(provided, expect=dict, cache=type_cache)
        assert disassembled.original is provided
        assert disassembled.optional is False
        assert disassembled.extracted == dict[str, int]
        assert disassembled.origin == dict
        assert disassembled.checkable == dict and isinstance(
            disassembled.checkable, InstanceCheckMeta
        )
        assert disassembled.annotation is None
        assert not disassembled.is_annotated
        assert disassembled.annotated is None
        assert disassembled.mro.all_vars == (str, int)
        assert disassembled.without_annotation == dict[str, int]
        assert disassembled.without_optional == dict[str, int]
        assert disassembled.nonoptional_union_types == ()
        assert disassembled.fields == []
        assert disassembled.fields_from == dict
        assert disassembled.fields_getter is None
        assert not attrs_has(disassembled.checkable)
        assert not is_dataclass(disassembled.checkable)
        assert disassembled.is_type_for({1: 2})
        assert not disassembled.is_type_for(None)
        assert disassembled.is_equivalent_type_for({3: 4})

        assert disassembled.for_display() == "dict[str, int]"

    it "works on optional builtin container to multiple simple types", type_cache: strcs.TypeCache:
        provided = tp.Optional[dict[str, int]]
        disassembled = Type.create(provided, expect=dict, cache=type_cache)
        assert disassembled.original is provided
        assert disassembled.optional is True
        assert disassembled.optional_outer is True
        assert disassembled.optional_inner is False
        assert disassembled.extracted == dict[str, int]
        assert disassembled.origin == dict
        assert disassembled.checkable == dict and isinstance(
            disassembled.checkable, InstanceCheckMeta
        )
        assert disassembled.annotation is None
        assert not disassembled.is_annotated
        assert disassembled.annotated is None
        assert disassembled.mro.all_vars == (str, int)
        assert disassembled.without_annotation == dict[str, int] | None
        assert disassembled.without_optional == dict[str, int]
        assert disassembled.nonoptional_union_types == ()
        assert disassembled.fields == []
        assert disassembled.fields_from == dict
        assert disassembled.fields_getter is None
        assert not attrs_has(disassembled.checkable)
        assert not is_dataclass(disassembled.checkable)
        assert disassembled.is_type_for({})
        assert disassembled.is_type_for(None)
        assert disassembled.is_equivalent_type_for({})

        assert disassembled.for_display() == "dict[str, int] | None"

    it "works on annotated optional builtin container to multiple simple types", type_cache: strcs.TypeCache:
        anno = "stuff"
        provided = tp.Annotated[tp.Optional[dict[str, int]], anno]
        disassembled = Type.create(provided, expect=dict, cache=type_cache)
        assert disassembled.original is provided
        assert disassembled.optional is True
        assert disassembled.optional_outer is False
        assert disassembled.optional_inner is True
        assert disassembled.extracted == dict[str, int]
        assert disassembled.origin == dict
        assert disassembled.checkable == dict and isinstance(
            disassembled.checkable, InstanceCheckMeta
        )
        assert disassembled.annotation is anno
        assert disassembled.is_annotated
        assert disassembled.annotated is provided
        assert disassembled.mro.all_vars == (str, int)
        assert disassembled.without_annotation == dict[str, int] | None
        assert disassembled.without_optional == tp.Annotated[dict[str, int], anno]
        assert disassembled.nonoptional_union_types == ()
        assert disassembled.fields == []
        assert disassembled.fields_from == dict
        assert disassembled.fields_getter is None
        assert not attrs_has(disassembled.checkable)
        assert not is_dataclass(disassembled.checkable)
        assert disassembled.is_type_for({})
        assert disassembled.is_type_for(None)
        assert disassembled.is_equivalent_type_for({})

        assert disassembled.for_display() == 'Annotated[dict[str, int] | None, "stuff"]'

    it "works on optional annotated builtin container to multiple simple types", type_cache: strcs.TypeCache:
        anno = "stuff"
        provided = tp.Optional[tp.Annotated[dict[str, int], anno]]
        disassembled = Type.create(provided, expect=dict, cache=type_cache)
        assert disassembled.original is provided
        assert disassembled.optional is True
        assert disassembled.optional_outer is True
        assert disassembled.optional_inner is False
        assert disassembled.extracted == dict[str, int]
        assert disassembled.origin == dict
        assert disassembled.checkable == dict and isinstance(
            disassembled.checkable, InstanceCheckMeta
        )
        assert disassembled.annotation is anno
        assert disassembled.is_annotated
        assert disassembled.annotated is tp.Annotated[dict[str, int], anno]
        assert disassembled.mro.all_vars == (str, int)
        assert disassembled.without_annotation == dict[str, int] | None
        assert disassembled.without_optional == tp.Annotated[dict[str, int], anno]
        assert disassembled.nonoptional_union_types == ()
        assert disassembled.fields == []
        assert disassembled.fields_from == dict
        assert disassembled.fields_getter is None
        assert not attrs_has(disassembled.checkable)
        assert not is_dataclass(disassembled.checkable)
        assert disassembled.is_type_for({})
        assert disassembled.is_type_for(None)
        assert disassembled.is_equivalent_type_for({})

        assert disassembled.for_display() == 'Annotated[dict[str, int], "stuff"] | None'

    it "works on an attrs class", type_cache: strcs.TypeCache, Dis: Disassembler:

        @define
        class Thing:
            one: int
            two: str

        provided = Thing
        disassembled = Type.create(provided, expect=Thing, cache=type_cache)
        assert disassembled.original is provided
        assert disassembled.optional is False
        assert disassembled.extracted == Thing
        assert disassembled.origin == Thing
        assert disassembled.checkable == Thing and isinstance(
            disassembled.checkable, InstanceCheckMeta
        )
        assert disassembled.annotation is None
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
        assert attrs_has(disassembled.checkable)
        assert not is_dataclass(disassembled.checkable)
        assert disassembled.is_type_for(Thing(one=1, two="two"))
        assert not disassembled.is_type_for(None)
        assert disassembled.is_equivalent_type_for(Thing(one=1, two="two"))

        @define
        class Child(Thing):
            pass

        assert disassembled.is_type_for(Child(one=1, two="two"))
        assert disassembled.is_equivalent_type_for(Child(one=1, two="two"))
        assert not Type.create(Child, cache=type_cache).is_equivalent_type_for(
            Thing(one=1, two="two")
        )

        assert disassembled.for_display() == "Thing"

    it "works on an dataclasses class", type_cache: strcs.TypeCache, Dis: Disassembler:

        @dataclass
        class Thing:
            one: int
            two: str

        provided = Thing
        disassembled = Type.create(provided, expect=Thing, cache=type_cache)
        assert disassembled.original is provided
        assert disassembled.optional is False
        assert disassembled.extracted == Thing
        assert disassembled.origin == Thing
        assert disassembled.checkable == Thing and isinstance(
            disassembled.checkable, InstanceCheckMeta
        )
        assert disassembled.annotation is None
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
        assert not attrs_has(disassembled.checkable)
        assert is_dataclass(disassembled.checkable)
        assert disassembled.is_type_for(Thing(one=1, two="two"))
        assert not disassembled.is_type_for(None)
        assert disassembled.is_equivalent_type_for(Thing(one=1, two="two"))

        @dataclass
        class Child(Thing):
            pass

        assert disassembled.is_type_for(Child(one=1, two="two"))
        assert disassembled.is_equivalent_type_for(Child(one=1, two="two"))
        assert not Type.create(Child, cache=type_cache).is_equivalent_type_for(
            Thing(one=1, two="two")
        )

        assert disassembled.for_display() == "Thing"

    it "works on a normal class", type_cache: strcs.TypeCache, Dis: Disassembler:

        class Thing:
            def __init__(self, one: int, two: str):
                self.one = one
                self.two = two

        provided = Thing
        disassembled = Type.create(provided, expect=Thing, cache=type_cache)
        assert disassembled.original is provided
        assert disassembled.optional is False
        assert disassembled.extracted == Thing
        assert disassembled.origin == Thing
        assert disassembled.checkable == Thing and isinstance(
            disassembled.checkable, InstanceCheckMeta
        )
        assert disassembled.annotation is None
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
        assert not attrs_has(disassembled.checkable)
        assert not is_dataclass(disassembled.checkable)
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

    it "works on inherited generic container", type_cache: strcs.TypeCache:

        class D(dict[str, int]):
            pass

        provided = D
        disassembled = Type.create(provided, expect=D, cache=type_cache)
        assert disassembled.original is provided
        assert disassembled.optional is False
        assert disassembled.extracted == D
        assert disassembled.origin == D
        assert disassembled.checkable == D and isinstance(disassembled.checkable, InstanceCheckMeta)
        assert disassembled.annotation is None
        assert not disassembled.is_annotated
        assert disassembled.annotated is None
        assert disassembled.mro.all_vars == (str, int)
        assert disassembled.without_annotation == D
        assert disassembled.without_optional == D
        assert disassembled.nonoptional_union_types == ()
        assert disassembled.fields == []
        assert disassembled.fields_from == D
        assert disassembled.fields_getter == Partial(fields_from_class, type_cache)
        assert not attrs_has(disassembled.checkable)
        assert not is_dataclass(disassembled.checkable)
        assert disassembled.is_type_for(D())
        assert not disassembled.is_type_for(None)
        assert disassembled.is_equivalent_type_for(D())

        assert disassembled.for_display() == "D"

    it "works on class with complicated hierarchy", type_cache: strcs.TypeCache, Dis: Disassembler:

        class Thing(tp.Generic[T, U]):
            def __init__(self, one: int, two: str):
                self.one = one
                self.two = two

        class Stuff(tp.Generic[T], Thing[int, T]):
            def __init__(self, one: int, two: str, three: bool):
                super().__init__(one, two)
                self.three = three

        class Blah(tp.Generic[U], Stuff[str]):
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
        assert disassembled.origin == Tree
        assert disassembled.checkable == Tree and isinstance(
            disassembled.checkable, InstanceCheckMeta
        )
        assert disassembled.annotation is None
        assert not disassembled.is_annotated
        assert disassembled.annotated is None
        assert disassembled.mro.typevars == OrderedDict(
            [
                ((Blah, U), bool),
                ((Stuff, T), str),
                ((Thing, T), int),
                ((Thing, U), strcs.MRO.Referal(owner=Stuff, typevar=T, value=str)),
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
        assert not attrs_has(disassembled.checkable)
        assert not is_dataclass(disassembled.checkable)
        assert disassembled.is_type_for(Tree(four="asdf"))
        assert not disassembled.is_type_for(None)
        assert disassembled.is_equivalent_type_for(Tree(four="asdf"))

        assert disassembled.for_display() == "Tree"

    it "works on an annotated class", type_cache: strcs.TypeCache, Dis: Disassembler:

        @define
        class Thing:
            one: int
            two: str

        anno = "blah"

        provided = tp.Annotated[Thing, anno]
        disassembled = Type.create(provided, expect=Thing, cache=type_cache)
        assert disassembled.original is provided
        assert disassembled.optional is False
        assert disassembled.extracted == Thing
        assert disassembled.origin == Thing
        assert disassembled.checkable == Thing and isinstance(
            disassembled.checkable, InstanceCheckMeta
        )
        assert disassembled.annotation is anno
        assert disassembled.is_annotated
        assert disassembled.annotated is provided
        assert disassembled.without_annotation == Thing
        assert disassembled.without_optional == tp.Annotated[Thing, anno]
        assert disassembled.nonoptional_union_types == ()
        assert disassembled.fields == [
            Field(name="one", owner=Thing, disassembled_type=Dis(int)),
            Field(name="two", owner=Thing, disassembled_type=Dis(str)),
        ]
        assert disassembled.fields_from == Thing
        assert disassembled.fields_getter == Partial(fields_from_attrs, type_cache)
        assert attrs_has(disassembled.checkable)
        assert not is_dataclass(disassembled.checkable)
        assert disassembled.is_type_for(Thing(one=1, two="two"))
        assert not disassembled.is_type_for(None)
        assert disassembled.is_equivalent_type_for(Thing(one=1, two="two"))

        @define
        class Child(Thing):
            pass

        assert disassembled.is_type_for(Child(one=1, two="two"))
        assert disassembled.is_equivalent_type_for(Child(one=1, two="two"))
        assert not Type.create(Child, cache=type_cache).is_equivalent_type_for(
            Thing(one=1, two="two")
        )

        assert disassembled.for_display() == 'Annotated[Thing, "blah"]'

    it "works on an optional annotated class", type_cache: strcs.TypeCache, Dis: Disassembler:

        @dataclass
        class Thing:
            one: int
            two: str

        anno = "blah"

        provided = tp.Annotated[tp.Optional[Thing], anno]
        disassembled = Type.create(provided, expect=Thing, cache=type_cache)
        assert disassembled.original is provided
        assert disassembled.optional is True
        assert disassembled.optional_outer is False
        assert disassembled.optional_inner is True
        assert disassembled.extracted == Thing
        assert disassembled.origin == Thing
        assert disassembled.checkable == Thing and isinstance(
            disassembled.checkable, InstanceCheckMeta
        )
        assert disassembled.annotation is anno
        assert disassembled.is_annotated
        assert disassembled.annotated is provided
        assert disassembled.without_annotation == Thing | None
        assert disassembled.without_optional == tp.Annotated[Thing, anno]
        assert disassembled.nonoptional_union_types == ()
        assert disassembled.fields == [
            Field(name="one", owner=Thing, disassembled_type=Dis(int)),
            Field(name="two", owner=Thing, disassembled_type=Dis(str)),
        ]
        assert disassembled.fields_from == Thing
        assert disassembled.fields_getter == Partial(fields_from_dataclasses, type_cache)
        assert not attrs_has(disassembled.checkable)
        assert is_dataclass(disassembled.checkable)
        assert disassembled.is_type_for(Thing(one=1, two="two"))
        assert disassembled.is_type_for(None)
        assert disassembled.is_equivalent_type_for(Thing(one=1, two="two"))

        @dataclass
        class Child(Thing):
            pass

        assert disassembled.is_type_for(Child(one=1, two="two"))
        assert disassembled.is_equivalent_type_for(Child(one=1, two="two"))
        assert not Type.create(Child, cache=type_cache).is_equivalent_type_for(
            Thing(one=1, two="two")
        )

        assert disassembled.for_display() == 'Annotated[Thing | None, "blah"]'

    it "works on an optional annotated generic class", type_cache: strcs.TypeCache, Dis: Disassembler:

        @dataclass
        class Thing(tp.Generic[T, U]):
            one: T
            two: U

        anno = "blah"

        provided = tp.Annotated[tp.Optional[Thing[int, str]], anno]
        disassembled = Type.create(provided, expect=Thing, cache=type_cache)
        assert disassembled.original is provided
        assert disassembled.optional is True
        assert disassembled.optional_outer is False
        assert disassembled.optional_inner is True
        assert disassembled.extracted == Thing[int, str]
        assert disassembled.origin == Thing
        assert disassembled.checkable == Thing and isinstance(
            disassembled.checkable, InstanceCheckMeta
        )
        assert disassembled.annotation is anno
        assert disassembled.is_annotated
        assert disassembled.annotated is provided
        assert disassembled.mro.all_vars == (int, str)
        assert disassembled.without_annotation == Thing[int, str] | None
        assert disassembled.without_optional == tp.Annotated[Thing[int, str], anno]
        assert disassembled.nonoptional_union_types == ()
        assert disassembled.fields == [
            Field(name="one", owner=Thing, disassembled_type=Dis(int)),
            Field(name="two", owner=Thing, disassembled_type=Dis(str)),
        ]
        assert disassembled.fields_from == Thing
        assert disassembled.fields_getter == Partial(fields_from_dataclasses, type_cache)
        assert not attrs_has(disassembled.checkable)
        assert is_dataclass(disassembled.checkable)
        assert disassembled.is_type_for(Thing(one=1, two="two"))
        assert disassembled.is_type_for(None)
        assert disassembled.is_equivalent_type_for(Thing(one=1, two="two"))

        @dataclass
        class Child(Thing):
            pass

        assert disassembled.is_type_for(Child(one=1, two="two"))
        assert disassembled.is_equivalent_type_for(Child(one=1, two="two"))
        assert not Type.create(Child, cache=type_cache).is_equivalent_type_for(
            Thing(one=1, two="two")
        )

        assert disassembled.for_display() == 'Annotated[Thing[int, str] | None, "blah"]'

    it "works on an optional annotated generic class without concrete types", type_cache: strcs.TypeCache, Dis: Disassembler:

        @define
        class Thing(tp.Generic[T, U]):
            one: T
            two: U

        anno = "blah"

        provided = tp.Annotated[tp.Optional[Thing], anno]
        disassembled = Type.create(provided, expect=Thing, cache=type_cache)
        assert disassembled.original is provided
        assert disassembled.optional is True
        assert disassembled.optional_outer is False
        assert disassembled.optional_inner is True
        assert disassembled.extracted == Thing
        assert disassembled.origin == Thing
        assert disassembled.checkable == Thing and isinstance(
            disassembled.checkable, InstanceCheckMeta
        )
        assert disassembled.annotation is anno
        assert disassembled.is_annotated
        assert disassembled.annotated is provided
        assert disassembled.mro.all_vars == (strcs.Type.Missing, strcs.Type.Missing)
        assert disassembled.without_annotation == Thing | None
        assert disassembled.without_optional == tp.Annotated[Thing, anno]
        assert disassembled.nonoptional_union_types == ()
        assert disassembled.fields == [
            Field(name="one", owner=Thing, disassembled_type=Dis(object)),
            Field(name="two", owner=Thing, disassembled_type=Dis(object)),
        ]
        assert disassembled.fields_from == Thing
        assert disassembled.fields_getter == Partial(fields_from_attrs, type_cache)
        assert attrs_has(disassembled.checkable)
        assert not is_dataclass(disassembled.checkable)
        assert disassembled.is_type_for(Thing(one=1, two="two"))
        assert disassembled.is_type_for(None)
        assert disassembled.is_equivalent_type_for(Thing(one=1, two="two"))

        @define
        class Child(Thing):
            pass

        assert disassembled.is_type_for(Child(one=1, two="two"))
        assert disassembled.is_equivalent_type_for(Child(one=1, two="two"))
        assert not Type.create(Child, cache=type_cache).is_equivalent_type_for(
            Thing(one=1, two="two")
        )

        assert disassembled.for_display() == 'Annotated[Thing[~T, ~U] | None, "blah"]'

    it "works on an optional annotated generic class with concrete types", type_cache: strcs.TypeCache, Dis: Disassembler:

        @define
        class Thing(tp.Generic[T, U]):
            one: T
            two: U

        anno = "blah"

        provided = tp.Annotated[tp.Optional[Thing[int, str]], anno]
        disassembled = Type.create(provided, expect=Thing, cache=type_cache)
        assert disassembled.original is provided
        assert disassembled.optional is True
        assert disassembled.optional_outer is False
        assert disassembled.optional_inner is True
        assert disassembled.extracted == Thing[int, str]
        assert disassembled.origin == Thing
        assert disassembled.checkable == Thing and isinstance(
            disassembled.checkable, InstanceCheckMeta
        )
        assert disassembled.annotation is anno
        assert disassembled.is_annotated
        assert disassembled.annotated is provided
        assert disassembled.mro.all_vars == (strcs.Type.Missing, strcs.Type.Missing)
        assert disassembled.without_annotation == Thing[int, str] | None
        assert disassembled.without_optional == tp.Annotated[Thing[int, str], anno]
        assert disassembled.nonoptional_union_types == ()
        assert disassembled.fields == [
            Field(name="one", owner=Thing, disassembled_type=Dis(int)),
            Field(name="two", owner=Thing, disassembled_type=Dis(str)),
        ]
        assert disassembled.fields_from == Thing
        assert disassembled.fields_getter == Partial(fields_from_attrs, type_cache)
        assert attrs_has(disassembled.checkable)
        assert not is_dataclass(disassembled.checkable)
        assert disassembled.is_type_for(Thing(one=1, two="two"))
        assert disassembled.is_type_for(None)
        assert disassembled.is_equivalent_type_for(Thing(one=1, two="two"))

        @define
        class Child(Thing):
            pass

        assert disassembled.is_type_for(Child(one=1, two="two"))
        assert disassembled.is_equivalent_type_for(Child(one=1, two="two"))
        assert not Type.create(Child, cache=type_cache).is_equivalent_type_for(
            Thing(one=1, two="two")
        )

        assert disassembled.for_display() == 'Annotated[Thing[int, str] | None, "blah"]'

describe "getting fields":

    it "works when there is a chain", type_cache: strcs.TypeCache, Dis: Disassembler:

        @define
        class Stuff:
            thing: "Thing"

        @define
        class Thing:
            stuff: tp.Optional["Stuff"]

        resolve_types(Thing, globals(), locals(), type_cache=type_cache)

        disassembled = Type.create(Thing, expect=Thing, cache=type_cache)
        assert disassembled.fields == [
            Field(name="stuff", owner=Thing, disassembled_type=Dis(Stuff | None))
        ]

    it "works on normal class", type_cache: strcs.TypeCache, Dis: Disassembler:

        class Thing:
            def __init__(self, one: int, /, two: str, *, three: bool = False, **kwargs):
                pass

        disassembled = Type.create(Thing, expect=Thing, cache=type_cache)
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

    it "works on attrs class", type_cache: strcs.TypeCache, Dis: Disassembler:

        @define
        class Thing:
            one: int
            two: str = "one"
            three: bool = attrs.field(kw_only=True, default=False)

        disassembled = Type.create(Thing, expect=Thing, cache=type_cache)
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

    it "works on dataclasses class", type_cache: strcs.TypeCache, Dis: Disassembler:

        @dataclass
        class Thing:
            one: int
            two: str = "one"
            three: bool = dataclasses.field(kw_only=True, default=False)

        disassembled = Type.create(Thing, expect=Thing, cache=type_cache)
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

describe "annotations":
    it "can return no annotation", type_cache: strcs.TypeCache:
        assert Type.create(int, cache=type_cache).ann is None
        assert Type.create(int | None, cache=type_cache).ann is None
        assert Type.create(int | str, cache=type_cache).ann is None
        assert Type.create(int | str | None, cache=type_cache).ann is None
        assert Type.create(list[int], cache=type_cache).ann is None
        assert Type.create(list[int] | None, cache=type_cache).ann is None

        class Thing:
            pass

        assert Type.create(Thing, cache=type_cache).ann is None

    it "can return an annotation with new creator", type_cache: strcs.TypeCache:

        def creator(value: object, /, _meta: strcs.Meta):
            ...

        ann = Type.create(tp.Annotated[int, creator], expect=int, cache=type_cache).ann
        assert isinstance(ann, strcs.Ann)
        assert ann.creator is creator

    it "can return an annotation with new adjustable meta", type_cache: strcs.TypeCache:

        class AdjustMeta:
            @classmethod
            def adjusted_meta(
                cls, meta: strcs.Meta, typ: strcs.Type, type_cache: strcs.TypeCache
            ) -> strcs.Meta:
                return meta.clone({"one": 1})

        adjustment = AdjustMeta()
        ann = Type.create(tp.Annotated[int, adjustment], expect=int, cache=type_cache).ann
        assert ann is adjustment
        assert isinstance(ann, strcs.AdjustableMeta)

        meta = strcs.Meta({"two": 2})
        m = ann.adjusted_meta(meta, Type.create(int, cache=type_cache), type_cache)
        assert m.data == {"one": 1, "two": 2}
        assert meta.data == {"two": 2}

    it "can return an annotation with new MetaAnnotation", type_cache: strcs.TypeCache:

        @define
        class Info(strcs.MetaAnnotation):
            three: str

        info = Info(three="three")
        ann = Type.create(tp.Annotated[int, info], expect=int, cache=type_cache).ann
        assert isinstance(ann, strcs.Ann), ann
        assert ann.creator is None
        assert ann.meta is info

        meta = strcs.Meta({"two": 2})
        m = ann.adjusted_meta(meta, Type.create(int, cache=type_cache), type_cache)
        assert m.data == {"__call_defined_annotation__": info, "two": 2}
        assert meta.data == {"two": 2}

    it "can return an annotation with new MergedMetaAnnotation", type_cache: strcs.TypeCache:

        @define
        class Info(strcs.MergedMetaAnnotation):
            three: str

        info = Info(three="three")
        ann = Type.create(tp.Annotated[int, info], expect=int, cache=type_cache).ann
        assert isinstance(ann, strcs.Ann), ann
        assert ann.creator is None
        assert ann.meta is info

        meta = strcs.Meta({"two": 2})
        m = ann.adjusted_meta(meta, Type.create(int, cache=type_cache), type_cache)
        assert m.data == {"three": "three", "two": 2}
        assert meta.data == {"two": 2}

    it "can return an annotation with new Ann", type_cache: strcs.TypeCache:

        def creator1(args: strcs.CreateArgs[int]) -> int:
            return 2

        def creator2(value: object) -> strcs.ConvertResponse[int]:
            ...

        class A(strcs.Ann[int]):
            def adjusted_meta(
                self, meta: strcs.Meta, typ: strcs.Type[int], type_cache: strcs.TypeCache
            ) -> strcs.Meta:
                return meta.clone({"one": 1})

        a = A(creator=creator2)
        ann = Type.create(tp.Annotated[int, a], expect=int, cache=type_cache).ann
        assert isinstance(ann, strcs.Ann), ann
        assert ann is a

        meta = strcs.Meta({"two": 2})
        m = ann.adjusted_meta(meta, Type.create(int, cache=type_cache), type_cache)
        assert m.data == {"one": 1, "two": 2}
        assert meta.data == {"two": 2}

        reg = strcs.CreateRegister()
        assert (
            ann.adjusted_creator(creator1, reg, Type.create(int, cache=type_cache), type_cache)
            == creator2
        )

describe "equality":
    it "matches any Type against Type.Missing", type_cache: strcs.TypeCache:
        typ = strcs.Type.create(int, expect=object, cache=type_cache)
        assert typ == strcs.Type.Missing

        typ2 = strcs.Type.create(tp.Annotated[None, 1], expect=object, cache=type_cache)
        assert typ2 == strcs.Type.Missing

        class Thing:
            pass

        typ3 = strcs.Type.create(Thing | None, expect=object, cache=type_cache)
        assert typ3 == strcs.Type.Missing

    it "matches against checkable instances and original type", type_cache: strcs.TypeCache:
        typ = strcs.Type.create(int, expect=object, cache=type_cache)
        assert typ == int
        assert typ == typ.checkable

        typ2 = strcs.Type.create(int, expect=object, cache=type_cache)
        assert typ2 == int
        assert typ2 == typ.checkable

        class Thing:
            pass

        typ3 = strcs.Type.create(tp.Annotated[Thing, 1], expect=object, cache=type_cache)
        assert typ3 == Thing
        assert typ3 == typ3.checkable
        assert typ3 != typ2.checkable
        assert typ2 != typ3.checkable

    it "matches against optionals", type_cache: strcs.TypeCache:
        typ = strcs.Type.create(int, expect=object, cache=type_cache)
        nun = None
        assert typ != nun
        assert typ == int
        assert typ == typ.checkable

        typ2 = strcs.Type.create(int | None, expect=object, cache=type_cache)
        assert typ2 == nun
        assert typ2 == int
        assert typ2 == typ.checkable

        class Thing:
            pass

        typ3 = strcs.Type.create(tp.Annotated[Thing | None, 1], expect=object, cache=type_cache)
        assert typ3 == Thing
        assert typ3 == nun
        assert typ3 == typ3.checkable
        assert typ3 != typ2.checkable
        assert typ2 != typ3.checkable

    it "matches against unions and partial unions", type_cache: strcs.TypeCache:
        typ = strcs.Type.create(int, expect=object, cache=type_cache)
        nun = None
        assert typ != nun
        assert typ == int
        assert typ != str
        assert typ == typ.checkable

        typ2 = strcs.Type.create(int | bool | str | None, expect=object, cache=type_cache)
        assert typ2 == nun
        assert typ2 == int
        assert typ2 == str
        assert typ2 == int | str
        assert typ2 == bool | str
        assert typ2 == int | None
        assert typ2 == typ.checkable

        class Thing:
            pass

        typ3 = strcs.Type.create(
            tp.Annotated[Thing | bool | None, 1], expect=object, cache=type_cache
        )
        assert typ3 == Thing
        assert typ3 == nun
        assert typ3 != str
        assert typ3 == bool
        assert typ3 == typ3.checkable
        # Typ2 has things not in this union
        assert typ3 != typ2.checkable
        assert typ2 != typ3.checkable

describe "Finding provided subtype":

    it "can find the provided subtype", type_cache: strcs.TypeCache:

        class Item:
            pass

        class ItemA(Item):
            pass

        class ItemB(Item):
            pass

        class ItemC(Item):
            pass

        I = tp.TypeVar("I", bound=Item)

        class Container(tp.Generic[I]):
            pass

        container_a = strcs.Type.create(Container[ItemA], expect=object, cache=type_cache)
        container_b = strcs.Type.create(Container[ItemB], expect=object, cache=type_cache)
        container_c = strcs.Type.create(Container[ItemC], expect=object, cache=type_cache)

        assert container_a.find_generic_subtype(Item) == (ItemA,)
        assert container_b.find_generic_subtype(Item) == (ItemB,)
        assert container_c.find_generic_subtype(Item) == (ItemC,)

    it "can find multiple subtypes", type_cache: strcs.TypeCache:

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

        O = tp.TypeVar("O", bound=One)
        T = tp.TypeVar("T", bound=Two)

        class Container(tp.Generic[O, T]):
            pass

        container_a = strcs.Type.create(Container[OneA, TwoB], expect=object, cache=type_cache)
        container_b = strcs.Type.create(Container[OneB, TwoB], expect=object, cache=type_cache)

        assert container_a.find_generic_subtype(One, Two) == (OneA, TwoB)
        assert container_b.find_generic_subtype(One, Two) == (OneB, TwoB)

    it "can find a partial number of subtypes", type_cache: strcs.TypeCache:

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

        O = tp.TypeVar("O", bound=One)
        T = tp.TypeVar("T", bound=Two)

        class Container(tp.Generic[O, T]):
            pass

        container_a = strcs.Type.create(Container[OneA, TwoA], expect=object, cache=type_cache)
        assert container_a.find_generic_subtype(One) == (OneA,)

    it "complains if want too many types", type_cache: strcs.TypeCache:

        class One:
            pass

        class Two:
            pass

        class OneA(One):
            pass

        class OneB(One):
            pass

        O = tp.TypeVar("O", bound=One)

        class Container(tp.Generic[O]):
            pass

        container_a = strcs.Type.create(Container[OneA], expect=object, cache=type_cache)
        with pytest.raises(
            ValueError, match=re.escape("The type has less typevars (1) than wanted (2)")
        ):
            container_a.find_generic_subtype(One, Two)

    it "complains if want wrong subtype", type_cache: strcs.TypeCache:

        class One:
            pass

        class Two:
            pass

        class OneA(One):
            pass

        class OneB(One):
            pass

        O = tp.TypeVar("O", bound=One)

        class Container(tp.Generic[O]):
            pass

        container_a = strcs.Type.create(Container[OneA], expect=object, cache=type_cache)
        with pytest.raises(
            ValueError,
            match="The concrete type <class '[^']+'> is not a subclass of what was asked for <class '[^']+'>",
        ):
            container_a.find_generic_subtype(Two)
