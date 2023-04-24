# coding: spec
import dataclasses
import inspect
import types
import typing as tp
from dataclasses import dataclass, is_dataclass

import attrs
import pytest
from attrs import define
from attrs import has as attrs_has

import strcs
from strcs import InstanceCheck, InstanceCheckMeta, Type, resolve_types
from strcs.disassemble import (
    Default,
    Field,
    fields_from_attrs,
    fields_from_class,
    fields_from_dataclasses,
)

from .test_helpers import assertParams


@pytest.fixture()
def type_cache() -> strcs.TypeCache:
    return strcs.TypeCache()


T = tp.TypeVar("T")
U = tp.TypeVar("U")

describe "Type":
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
        assert disassembled.fields == []
        assert disassembled.fields_from == int
        assert disassembled.fields_getter is None
        assert not attrs_has(disassembled.checkable)
        assert not is_dataclass(disassembled.checkable)
        assert disassembled.is_type_for(1)
        assert not disassembled.is_type_for(None)
        assert disassembled.is_equivalent_type_for(3)

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
        assert not disassembled.is_annotated
        assert disassembled.without_annotation == int | str
        assert disassembled.without_optional == int | str
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

    it "works on a complicated union", type_cache: strcs.TypeCache:
        provided = tp.Union[tp.Annotated[list[int], "str"], tp.Annotated[int | str | None, "hello"]]
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
        assert disassembled.fields == []
        assert disassembled.fields_from == int
        assert disassembled.fields_getter is None
        assert not attrs_has(disassembled.checkable)
        assert not is_dataclass(disassembled.checkable)
        assert disassembled.is_type_for(1)
        assert disassembled.is_type_for(None)
        assert disassembled.is_equivalent_type_for(3)

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
        assert disassembled.fields == []
        assert disassembled.fields_from == int
        assert disassembled.fields_getter is None
        assert not attrs_has(disassembled.checkable)
        assert not is_dataclass(disassembled.checkable)
        assert disassembled.is_type_for(1)
        assert not disassembled.is_type_for(None)
        assert disassembled.is_equivalent_type_for(3)

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
        assert disassembled.fields == []
        assert disassembled.fields_from == int
        assert disassembled.fields_getter is None
        assert not attrs_has(disassembled.checkable)
        assert not is_dataclass(disassembled.checkable)
        assert disassembled.is_type_for(1)
        assert disassembled.is_type_for(None)
        assert disassembled.is_equivalent_type_for(3)

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
        assert disassembled.without_annotation == list[int]
        assert disassembled.without_optional == list[int]
        assert disassembled.fields == []
        assert disassembled.fields_from == list
        assert disassembled.fields_getter is None
        assert not attrs_has(disassembled.checkable)
        assert not is_dataclass(disassembled.checkable)
        assert disassembled.is_type_for([])
        assert not disassembled.is_type_for(None)
        assert disassembled.is_equivalent_type_for([1])

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
        assert disassembled.without_annotation == list[int] | None
        assert disassembled.without_optional == list[int]
        assert disassembled.fields == []
        assert disassembled.fields_from == list
        assert disassembled.fields_getter is None
        assert not attrs_has(disassembled.checkable)
        assert not is_dataclass(disassembled.checkable)
        assert disassembled.is_type_for([])
        assert disassembled.is_type_for(None)
        assert disassembled.is_equivalent_type_for([12])

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
        assert disassembled.without_annotation == dict[str, int]
        assert disassembled.without_optional == dict[str, int]
        assert disassembled.fields == []
        assert disassembled.fields_from == dict
        assert disassembled.fields_getter is None
        assert not attrs_has(disassembled.checkable)
        assert not is_dataclass(disassembled.checkable)
        assert disassembled.is_type_for({1: 2})
        assert not disassembled.is_type_for(None)
        assert disassembled.is_equivalent_type_for({3: 4})

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
        assert disassembled.without_annotation == dict[str, int] | None
        assert disassembled.without_optional == dict[str, int]
        assert disassembled.fields == []
        assert disassembled.fields_from == dict
        assert disassembled.fields_getter is None
        assert not attrs_has(disassembled.checkable)
        assert not is_dataclass(disassembled.checkable)
        assert disassembled.is_type_for({})
        assert disassembled.is_type_for(None)
        assert disassembled.is_equivalent_type_for({})

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
        assert disassembled.without_annotation == dict[str, int] | None
        assert disassembled.without_optional == tp.Annotated[dict[str, int], anno]
        assert disassembled.fields == []
        assert disassembled.fields_from == dict
        assert disassembled.fields_getter is None
        assert not attrs_has(disassembled.checkable)
        assert not is_dataclass(disassembled.checkable)
        assert disassembled.is_type_for({})
        assert disassembled.is_type_for(None)
        assert disassembled.is_equivalent_type_for({})

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
        assert disassembled.without_annotation == dict[str, int] | None
        assert disassembled.without_optional == tp.Annotated[dict[str, int], anno]
        assert disassembled.fields == []
        assert disassembled.fields_from == dict
        assert disassembled.fields_getter is None
        assert not attrs_has(disassembled.checkable)
        assert not is_dataclass(disassembled.checkable)
        assert disassembled.is_type_for({})
        assert disassembled.is_type_for(None)
        assert disassembled.is_equivalent_type_for({})

    it "works on an attrs class", type_cache: strcs.TypeCache:

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
        assert disassembled.fields == [
            Field(name="one", owner=Thing, type=int),
            Field(name="two", owner=Thing, type=str),
        ]
        assert disassembled.fields_from == Thing
        assert disassembled.fields_getter == fields_from_attrs
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

    it "works on an dataclasses class", type_cache: strcs.TypeCache:

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
        assert disassembled.fields == [
            Field(name="one", owner=Thing, type=int),
            Field(name="two", owner=Thing, type=str),
        ]
        assert disassembled.fields_from == Thing
        assert disassembled.fields_getter == fields_from_dataclasses
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

    it "works on a normal class", type_cache: strcs.TypeCache:

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
        assert disassembled.fields == [
            Field(name="one", owner=Thing, type=int),
            Field(name="two", owner=Thing, type=str),
        ]
        assert disassembled.fields_from == Thing
        assert disassembled.fields_getter is fields_from_class
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

    it "works on an annotated class", type_cache: strcs.TypeCache:

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
        assert disassembled.fields == [
            Field(name="one", owner=Thing, type=int),
            Field(name="two", owner=Thing, type=str),
        ]
        assert disassembled.fields_from == Thing
        assert disassembled.fields_getter == fields_from_attrs
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

    it "works on an optional annotated class", type_cache: strcs.TypeCache:

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
        assert disassembled.fields == [
            Field(name="one", owner=Thing, type=int),
            Field(name="two", owner=Thing, type=str),
        ]
        assert disassembled.fields_from == Thing
        assert disassembled.fields_getter == fields_from_dataclasses
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

    it "works on an optional annotated generic class", type_cache: strcs.TypeCache:

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
        typevar_map, typevars = disassembled.generics
        assert typevars == [T, U]
        assert typevar_map == {T: int, U: str}
        assert disassembled.without_annotation == Thing[int, str] | None
        assert disassembled.without_optional == tp.Annotated[Thing[int, str], anno]
        assert disassembled.fields == [
            Field(name="one", owner=Thing, type=int),
            Field(name="two", owner=Thing, type=str),
        ]
        assert disassembled.fields_from == Thing
        assert disassembled.fields_getter == fields_from_dataclasses
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

    it "works on an optional annotated generic class without concrete types", type_cache: strcs.TypeCache:

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
        assert disassembled.without_annotation == Thing | None
        assert disassembled.without_optional == tp.Annotated[Thing, anno]
        assert disassembled.fields == [
            Field(name="one", owner=Thing, type=object),
            Field(name="two", owner=Thing, type=object),
        ]
        assert disassembled.fields_from == Thing
        assert disassembled.fields_getter == fields_from_attrs
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

describe "getting fields":
    it "works when there is a chain", type_cache: strcs.TypeCache:

        @define
        class Stuff:
            thing: "Thing"

        @define
        class Thing:
            stuff: tp.Optional["Stuff"]

        resolve_types(Thing, globals(), locals(), type_cache=type_cache)

        disassembled = Type.create(Thing, expect=Thing, cache=type_cache)
        assert disassembled.fields == [Field(name="stuff", owner=Thing, type=Stuff | None)]

    it "works on normal class", type_cache: strcs.TypeCache:

        class Thing:
            def __init__(self, one: int, /, two: str, *, three: bool = False, **kwargs):
                pass

        disassembled = Type.create(Thing, expect=Thing, cache=type_cache)
        assert disassembled.fields_getter is fields_from_class
        assert disassembled.fields_from is Thing
        assertParams(
            disassembled.fields,
            [
                Field(name="one", owner=Thing, kind=inspect.Parameter.POSITIONAL_ONLY, type=int),
                Field(
                    name="two", owner=Thing, kind=inspect.Parameter.POSITIONAL_OR_KEYWORD, type=str
                ),
                Field(
                    name="three",
                    owner=Thing,
                    kind=inspect.Parameter.KEYWORD_ONLY,
                    type=bool,
                    default=Default(False),
                ),
                Field(name="", owner=Thing, kind=inspect.Parameter.VAR_KEYWORD, type=object),
            ],
        )

    it "works on attrs class", type_cache: strcs.TypeCache:

        @define
        class Thing:
            one: int
            two: str = "one"
            three: bool = attrs.field(kw_only=True, default=False)

        disassembled = Type.create(Thing, expect=Thing, cache=type_cache)
        assert disassembled.fields_getter is fields_from_attrs
        assert disassembled.fields_from is Thing
        assertParams(
            disassembled.fields,
            [
                Field(
                    name="one", owner=Thing, kind=inspect.Parameter.POSITIONAL_OR_KEYWORD, type=int
                ),
                Field(
                    name="two",
                    owner=Thing,
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    type=str,
                    default=Default("one"),
                ),
                Field(
                    name="three",
                    kind=inspect.Parameter.KEYWORD_ONLY,
                    owner=Thing,
                    type=bool,
                    default=Default(False),
                ),
            ],
        )

    it "works on dataclasses class", type_cache: strcs.TypeCache:

        @dataclass
        class Thing:
            one: int
            two: str = "one"
            three: bool = dataclasses.field(kw_only=True, default=False)

        disassembled = Type.create(Thing, expect=Thing, cache=type_cache)
        assert disassembled.fields_getter is fields_from_dataclasses
        assert disassembled.fields_from is Thing
        assertParams(
            disassembled.fields,
            [
                Field(
                    name="one", owner=Thing, kind=inspect.Parameter.POSITIONAL_OR_KEYWORD, type=int
                ),
                Field(
                    owner=Thing,
                    name="two",
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    type=str,
                    default=Default("one"),
                ),
                Field(
                    name="three",
                    owner=Thing,
                    kind=inspect.Parameter.KEYWORD_ONLY,
                    type=bool,
                    default=Default(False),
                ),
            ],
        )

describe "checkable":
    it "can find instances and subclasses of basic types", type_cache: strcs.TypeCache:
        db = Type.create(int, expect=int, cache=type_cache)
        assert isinstance(23, db.checkable)
        assert not isinstance(23.4, db.checkable)
        assert not isinstance("asdf", db.checkable)
        assert not isinstance({}, db.checkable)

        class MyInt(int):
            pass

        assert issubclass(int, db.checkable)
        assert issubclass(MyInt, db.checkable)
        assert issubclass(Type.create(MyInt, cache=type_cache).checkable, db.checkable)

        class NotMyInt:
            pass

        assert not issubclass(NotMyInt, db.checkable)
        assert not issubclass(Type.create(NotMyInt, cache=type_cache).checkable, db.checkable)
        assert not issubclass(float, db.checkable)
        assert not issubclass(dict, db.checkable)

        assert isinstance(db.checkable, InstanceCheckMeta)
        assert isinstance(db.checkable, type)
        assert isinstance(db.checkable, Type.create(type, cache=type_cache).checkable)

        assert issubclass(db.checkable, InstanceCheck)
        assert not issubclass(db.checkable, type)
        assert not issubclass(type, db.checkable)
        assert not issubclass(Type.create(type, cache=type_cache).checkable, db.checkable)
        assert not issubclass(db.checkable, Type.create(type, cache=type_cache).checkable)
        assert not isinstance(db.checkable, int)
        assert not isinstance(db.checkable, Type.create(int, cache=type_cache).checkable)
        assert not issubclass(db.checkable, NotMyInt)
        assert not issubclass(db.checkable, Type.create(NotMyInt, cache=type_cache).checkable)

        assert db.checkable.Meta.typ == int
        assert db.checkable.Meta.original == int
        assert not db.checkable.Meta.optional
        assert db.checkable.Meta.without_optional == int
        assert db.checkable.Meta.without_annotation == int

    it "can find instances and subclasses of union types", type_cache: strcs.TypeCache:
        db = Type.create(int | str, expect=types.UnionType, cache=type_cache)
        assert isinstance(23, db.checkable)
        assert not isinstance(23.4, db.checkable)
        assert isinstance("asdf", db.checkable)
        assert not isinstance({}, db.checkable)

        class MyInt(int):
            pass

        assert issubclass(MyInt, db.checkable)
        assert issubclass(int, db.checkable)
        assert issubclass(Type.create(MyInt, cache=type_cache).checkable, db.checkable)

        class MyString(str):
            pass

        assert issubclass(str, db.checkable)
        assert issubclass(MyString, db.checkable)
        assert issubclass(Type.create(MyString, cache=type_cache).checkable, db.checkable)

        class NotMyInt:
            pass

        assert not issubclass(NotMyInt, db.checkable)
        assert not issubclass(Type.create(NotMyInt, cache=type_cache).checkable, db.checkable)
        assert not issubclass(float, db.checkable)
        assert not issubclass(dict, db.checkable)

        assert isinstance(db.checkable, InstanceCheckMeta)
        assert isinstance(db.checkable, type)
        assert isinstance(db.checkable, Type.create(type, cache=type_cache).checkable)

        assert issubclass(db.checkable, InstanceCheck)
        assert not issubclass(db.checkable, type)
        assert not issubclass(type, db.checkable)
        assert not issubclass(Type.create(type, cache=type_cache).checkable, db.checkable)
        assert not issubclass(db.checkable, Type.create(type, cache=type_cache).checkable)
        assert not isinstance(db.checkable, int)
        assert not isinstance(db.checkable, Type.create(int, cache=type_cache).checkable)
        assert not issubclass(db.checkable, NotMyInt)
        assert not issubclass(db.checkable, str)
        assert not issubclass(db.checkable, Type.create(NotMyInt, cache=type_cache).checkable)

        assert db.checkable.Meta.typ == int | str
        assert db.checkable.Meta.original == int | str
        assert not db.checkable.Meta.optional
        assert db.checkable.Meta.without_optional == int | str
        assert db.checkable.Meta.without_annotation == int | str

    it "can find instances and subclasses of complicated union type", type_cache: strcs.TypeCache:
        provided = tp.Union[tp.Annotated[list[int], "str"], tp.Annotated[int | str | None, "hello"]]
        db = Type.create(provided, expect=types.UnionType, cache=type_cache)
        assert isinstance(23, db.checkable)
        assert not isinstance(23.4, db.checkable)
        assert isinstance("asdf", db.checkable)
        assert not isinstance({}, db.checkable)

        class MyInt(int):
            pass

        assert issubclass(MyInt, db.checkable)
        assert issubclass(int, db.checkable)
        assert issubclass(Type.create(MyInt, cache=type_cache).checkable, db.checkable)

        class MyString(str):
            pass

        assert issubclass(str, db.checkable)
        assert issubclass(MyString, db.checkable)
        assert issubclass(Type.create(MyString, cache=type_cache).checkable, db.checkable)

        class NotMyInt:
            pass

        assert not issubclass(NotMyInt, db.checkable)
        assert not issubclass(Type.create(NotMyInt, cache=type_cache).checkable, db.checkable)
        assert not issubclass(float, db.checkable)
        assert not issubclass(dict, db.checkable)

        assert isinstance(db.checkable, InstanceCheckMeta)
        assert isinstance(db.checkable, type)
        assert isinstance(db.checkable, Type.create(type, cache=type_cache).checkable)

        assert issubclass(db.checkable, InstanceCheck)
        assert not issubclass(db.checkable, type)
        assert not issubclass(type, db.checkable)
        assert not issubclass(Type.create(type, cache=type_cache).checkable, db.checkable)
        assert not issubclass(db.checkable, Type.create(type, cache=type_cache).checkable)
        assert not isinstance(db.checkable, int)
        assert not isinstance(db.checkable, Type.create(int, cache=type_cache).checkable)
        assert not issubclass(db.checkable, NotMyInt)
        assert not issubclass(db.checkable, str)
        assert not issubclass(db.checkable, Type.create(NotMyInt, cache=type_cache).checkable)

        assert db.checkable.Meta.typ == provided
        assert db.checkable.Meta.original == provided
        assert not db.checkable.Meta.optional
        assert db.checkable.Meta.without_optional == provided
        assert db.checkable.Meta.without_annotation == provided

    it "can find instances and subclasses of optional basic types", type_cache: strcs.TypeCache:
        db = Type.create(int | None, expect=int, cache=type_cache)
        assert isinstance(23, db.checkable)
        assert isinstance(None, db.checkable)
        assert not isinstance(23.4, db.checkable)
        assert not isinstance("asdf", db.checkable)

        class MyInt(int):
            pass

        assert issubclass(MyInt, db.checkable)
        assert issubclass(Type.create(MyInt, cache=type_cache).checkable, db.checkable)

        class NotMyInt:
            pass

        assert not issubclass(NotMyInt, db.checkable)
        assert not issubclass(Type.create(NotMyInt, cache=type_cache).checkable, db.checkable)

        assert isinstance(db.checkable, InstanceCheckMeta)
        assert isinstance(db.checkable, type)
        assert isinstance(db.checkable, Type.create(type, cache=type_cache).checkable)

        assert issubclass(db.checkable, InstanceCheck)
        assert not issubclass(db.checkable, type)
        assert not issubclass(type, db.checkable)
        assert not issubclass(Type.create(type, cache=type_cache).checkable, db.checkable)
        assert not issubclass(db.checkable, Type.create(type, cache=type_cache).checkable)
        assert not isinstance(db.checkable, int)
        assert not isinstance(db.checkable, Type.create(int, cache=type_cache).checkable)
        assert not issubclass(db.checkable, NotMyInt)
        assert not issubclass(db.checkable, Type.create(NotMyInt, cache=type_cache).checkable)

        assert db.checkable.Meta.typ == int
        assert db.checkable.Meta.original == int | None
        assert db.checkable.Meta.optional
        assert db.checkable.Meta.without_optional == int
        assert db.checkable.Meta.without_annotation == int | None

    it "can find instances and subclasses of annotated types", type_cache: strcs.TypeCache:
        db = Type.create(tp.Annotated[int | None, "stuff"], expect=int, cache=type_cache)
        assert isinstance(23, db.checkable)
        assert isinstance(None, db.checkable)
        assert not isinstance(23.4, db.checkable)
        assert not isinstance("asdf", db.checkable)

        class MyInt(int):
            pass

        assert issubclass(MyInt, db.checkable)
        assert issubclass(Type.create(MyInt, cache=type_cache).checkable, db.checkable)

        class NotMyInt:
            pass

        assert not issubclass(NotMyInt, db.checkable)
        assert not issubclass(Type.create(NotMyInt, cache=type_cache).checkable, db.checkable)

        assert isinstance(db.checkable, InstanceCheckMeta)
        assert isinstance(db.checkable, type)
        assert isinstance(db.checkable, Type.create(type, cache=type_cache).checkable)

        assert issubclass(db.checkable, InstanceCheck)
        assert not issubclass(db.checkable, type)
        assert not issubclass(type, db.checkable)
        assert not issubclass(Type.create(type, cache=type_cache).checkable, db.checkable)
        assert not issubclass(db.checkable, Type.create(type, cache=type_cache).checkable)
        assert not isinstance(db.checkable, int)
        assert not isinstance(db.checkable, Type.create(int, cache=type_cache).checkable)
        assert not issubclass(db.checkable, NotMyInt)
        assert not issubclass(db.checkable, Type.create(NotMyInt, cache=type_cache).checkable)

        assert db.checkable.Meta.typ == int
        assert db.checkable.Meta.original == tp.Annotated[int | None, "stuff"]
        assert db.checkable.Meta.optional
        assert db.checkable.Meta.without_optional == tp.Annotated[int, "stuff"]
        assert db.checkable.Meta.without_annotation == int | None

    it "can find instances and subclasses of user defined classes", type_cache: strcs.TypeCache:

        class Mine:
            pass

        db = Type.create(Mine, expect=Mine, cache=type_cache)
        assert not isinstance(23, db.checkable)
        assert not isinstance(23.4, db.checkable)
        assert not isinstance("asdf", db.checkable)
        assert isinstance(Mine(), db.checkable)

        class Child(Mine):
            pass

        assert isinstance(Child(), db.checkable)
        assert issubclass(Child, db.checkable)

        class MyInt(int):
            pass

        assert not issubclass(MyInt, db.checkable)

        class Other:
            pass

        assert not isinstance(Other(), db.checkable)
        assert not issubclass(Other, db.checkable)

        assert isinstance(db.checkable, InstanceCheckMeta)
        assert isinstance(db.checkable, type)
        assert isinstance(db.checkable, Type.create(type, cache=type_cache).checkable)

        assert issubclass(db.checkable, InstanceCheck)
        assert not issubclass(db.checkable, type)
        assert not issubclass(type, db.checkable)
        assert not issubclass(Type.create(type, cache=type_cache).checkable, db.checkable)
        assert not issubclass(db.checkable, Type.create(type, cache=type_cache).checkable)
        assert not isinstance(db.checkable, int)
        assert not isinstance(db.checkable, Type.create(int, cache=type_cache).checkable)
        assert not issubclass(db.checkable, Other)
        assert not issubclass(db.checkable, Type.create(Other, cache=type_cache).checkable)

        assert db.checkable.Meta.typ == Mine
        assert db.checkable.Meta.original == Mine
        assert not db.checkable.Meta.optional
        assert db.checkable.Meta.without_optional == Mine
        assert db.checkable.Meta.without_annotation == Mine

    it "can instantiate the provided type", type_cache: strcs.TypeCache:
        checkable = Type.create(dict[str, bool], cache=type_cache).checkable
        made = tp.cast(tp.Callable, checkable)([("1", True), ("2", False)])
        assert made == {"1": True, "2": False}

        assert checkable.Meta.typ == dict
        assert checkable.Meta.original == dict[str, bool]
        assert not checkable.Meta.optional
        assert checkable.Meta.without_optional == dict[str, bool]
        assert checkable.Meta.without_annotation == dict[str, bool]

        class Thing:
            def __init__(self, one: int):
                self.one = one

        checkable = Type.create(Thing, cache=type_cache).checkable
        made = tp.cast(tp.Callable, checkable)(one=1)
        assert isinstance(made, Thing)
        assert made.one == 1

        assert checkable.Meta.typ == Thing
        assert checkable.Meta.original == Thing
        assert not checkable.Meta.optional
        assert checkable.Meta.without_optional == Thing
        assert checkable.Meta.without_annotation == Thing

        constructor: tp.Callable = Type.create(int | str, cache=type_cache).checkable
        with pytest.raises(ValueError, match="Cannot instantiate a union type"):
            constructor(1)

    it "can get typing origin", type_cache: strcs.TypeCache:

        assert tp.get_origin(Type.create(str | int, cache=type_cache).checkable) == types.UnionType
        assert tp.get_origin(Type.create(dict[str, int], cache=type_cache).checkable) == dict
        assert tp.get_origin(Type.create(dict[str, int] | None, cache=type_cache).checkable) == dict
        assert (
            tp.get_origin(
                Type.create(tp.Annotated[dict[str, int] | None, "hi"], cache=type_cache).checkable
            )
            == dict
        )

        assert tp.get_origin(Type.create(dict, cache=type_cache).checkable) is None
        assert tp.get_origin(Type.create(dict | None, cache=type_cache).checkable) is None
        assert (
            tp.get_origin(Type.create(tp.Annotated[dict | None, "hi"], cache=type_cache).checkable)
            is None
        )

        assert tp.get_origin(Type.create(dict | str, cache=type_cache).checkable) is types.UnionType

        class Thing(tp.Generic[T]):
            pass

        assert tp.get_origin(Type.create(Thing, cache=type_cache).checkable) is None
        assert tp.get_origin(Type.create(Thing[int], cache=type_cache).checkable) is Thing

    it "can get typing args", type_cache: strcs.TypeCache:

        assert tp.get_args(Type.create(str | int, cache=type_cache).checkable) == (str, int)
        assert tp.get_args(Type.create(dict[str, int], cache=type_cache).checkable) == (str, int)
        assert tp.get_args(Type.create(dict[str, int] | None, cache=type_cache).checkable) == (
            str,
            int,
        )
        assert tp.get_args(
            Type.create(tp.Annotated[dict[str, int] | None, "hi"], cache=type_cache).checkable
        ) == (
            str,
            int,
        )

        assert tp.get_args(Type.create(dict, cache=type_cache).checkable) == ()
        assert tp.get_args(Type.create(dict | None, cache=type_cache).checkable) == ()
        assert (
            tp.get_args(Type.create(tp.Annotated[dict | None, "hi"], cache=type_cache).checkable)
            == ()
        )

        assert tp.get_args(Type.create(dict | str, cache=type_cache).checkable) == (dict, str)

        class Thing(tp.Generic[T]):
            pass

        assert tp.get_args(Type.create(Thing, cache=type_cache).checkable) == ()
        assert tp.get_args(Type.create(Thing[int], cache=type_cache).checkable) == (int,)

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
        assert isinstance(ann, strcs.AnnBase)
        assert ann.creator is creator

    it "can return an annotation with new adjustable meta", type_cache: strcs.TypeCache:

        class AdjustMeta:
            @classmethod
            def adjusted_meta(
                cls, meta: strcs.Meta, typ: strcs.Type, type_cache: strcs.TypeCache
            ) -> strcs.Meta:
                return meta.clone({"one": 1})

        ann = Type.create(tp.Annotated[int, AdjustMeta], expect=int, cache=type_cache).ann
        assert isinstance(ann, strcs.AnnBase), ann
        assert ann.creator is None
        assert ann.meta is AdjustMeta

        meta = strcs.Meta({"two": 2})
        m = ann.adjusted_meta(meta, Type.create(int, cache=type_cache), type_cache)
        assert m.data == {"one": 1, "two": 2}
        assert meta.data == {"two": 2}

    it "can return an annotation with new Annotation", type_cache: strcs.TypeCache:

        @define
        class Info(strcs.Annotation):
            three: str

        info = Info(three="three")
        ann = Type.create(tp.Annotated[int, info], expect=int, cache=type_cache).ann
        assert isinstance(ann, strcs.AnnBase), ann
        assert ann.creator is None
        assert ann.meta is info

        meta = strcs.Meta({"two": 2})
        m = ann.adjusted_meta(meta, Type.create(int, cache=type_cache), type_cache)
        assert m.data == {"__call_defined_annotation__": info, "two": 2}
        assert meta.data == {"two": 2}

    it "can return an annotation with new MergedAnnotation", type_cache: strcs.TypeCache:

        @define
        class Info(strcs.MergedAnnotation):
            three: str

        info = Info(three="three")
        ann = Type.create(tp.Annotated[int, info], expect=int, cache=type_cache).ann
        assert isinstance(ann, strcs.AnnBase), ann
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

        class A(strcs.AnnBase[int]):
            def adjusted_meta(
                self, meta: strcs.Meta, typ: strcs.Type[int], type_cache: strcs.TypeCache
            ) -> strcs.Meta:
                return meta.clone({"one": 1})

        a = A(creator=creator2)
        ann = Type.create(tp.Annotated[int, a], expect=int, cache=type_cache).ann
        assert isinstance(ann, strcs.AnnBase), ann
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
