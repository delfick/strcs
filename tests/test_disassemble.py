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

from strcs import Disassembled, InstanceCheck, InstanceCheckMeta, resolve_types
from strcs.disassemble import (
    Default,
    Field,
    fields_from_attrs,
    fields_from_class,
    fields_from_dataclasses,
)

from .test_disassemble_helpers import assertParams

T = tp.TypeVar("T")
U = tp.TypeVar("U")

describe "Type":
    it "works on simple type":
        provided = int
        disassembled = Disassembled.create(provided)
        assert disassembled.original is provided
        assert disassembled.optional is False
        assert disassembled.extracted == int
        assert disassembled.origin_or_type == int
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

    it "works on a union":
        provided = int | str
        disassembled = Disassembled.create(provided)
        assert disassembled.original is provided
        assert disassembled.optional is False
        assert disassembled.extracted == int | str
        assert disassembled.origin_or_type == types.UnionType
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

    it "works on a complicated union":
        provided = tp.Union[tp.Annotated[list[int], "str"], tp.Annotated[int | str | None, "hello"]]
        disassembled = Disassembled.create(provided)
        assert disassembled.original is provided
        assert disassembled.optional is False
        assert disassembled.extracted == provided
        assert disassembled.origin_or_type == tp.Union

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

    it "works on a typing union":
        provided = tp.Union[int, str]
        disassembled = Disassembled.create(provided)
        assert disassembled.original is provided
        assert disassembled.optional is False
        assert disassembled.extracted == int | str
        assert disassembled.origin_or_type == tp.Union
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

    it "works on an optional union":
        provided = int | str | None
        disassembled = Disassembled.create(provided)
        assert disassembled.original is provided
        assert disassembled.optional is True
        assert disassembled.extracted == int | str
        assert disassembled.origin_or_type == types.UnionType
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

    it "works on optional simple type":
        provided = int | None
        disassembled = Disassembled.create(provided)
        assert disassembled.original is provided
        assert disassembled.optional is True
        assert disassembled.optional_outer is True
        assert disassembled.optional_inner is False
        assert disassembled.extracted == int
        assert disassembled.origin_or_type == int
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

    it "works on annotated simple type":
        anno = "hello"
        provided = tp.Annotated[int, anno]
        disassembled = Disassembled.create(provided)
        assert disassembled.original is provided
        assert disassembled.optional is False
        assert disassembled.extracted == int
        assert disassembled.origin_or_type == int
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

    it "works on optional annotated simple type":
        anno = "hello"
        provided = tp.Annotated[tp.Optional[int], anno]
        disassembled = Disassembled.create(provided)
        assert disassembled.original is provided
        assert disassembled.optional is True
        assert disassembled.optional_outer is False
        assert disassembled.optional_inner is True
        assert disassembled.extracted == int
        assert disassembled.origin_or_type == int
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

    it "works on builtin container to simple type":
        provided = list[int]
        disassembled = Disassembled.create(provided)
        assert disassembled.original is provided
        assert disassembled.optional is False
        assert disassembled.extracted == list[int]
        assert disassembled.origin_or_type == list
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

    it "works on optional builtin container to simple type":
        provided = list[int] | None
        disassembled = Disassembled.create(provided)
        assert disassembled.original is provided
        assert disassembled.optional is True
        assert disassembled.optional_outer is True
        assert disassembled.optional_inner is False
        assert disassembled.extracted == list[int]
        assert disassembled.origin_or_type == list
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

    it "works on builtin container to multiple simple types":
        provided = dict[str, int]
        disassembled = Disassembled.create(provided)
        assert disassembled.original is provided
        assert disassembled.optional is False
        assert disassembled.extracted == dict[str, int]
        assert disassembled.origin_or_type == dict
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

    it "works on optional builtin container to multiple simple types":
        provided = tp.Optional[dict[str, int]]
        disassembled = Disassembled.create(provided)
        assert disassembled.original is provided
        assert disassembled.optional is True
        assert disassembled.optional_outer is True
        assert disassembled.optional_inner is False
        assert disassembled.extracted == dict[str, int]
        assert disassembled.origin_or_type == dict
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

    it "works on annotated optional builtin container to multiple simple types":
        anno = "stuff"
        provided = tp.Annotated[tp.Optional[dict[str, int]], anno]
        disassembled = Disassembled.create(provided)
        assert disassembled.original is provided
        assert disassembled.optional is True
        assert disassembled.optional_outer is False
        assert disassembled.optional_inner is True
        assert disassembled.extracted == dict[str, int]
        assert disassembled.origin_or_type == dict
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

    it "works on optional annotated builtin container to multiple simple types":
        anno = "stuff"
        provided = tp.Optional[tp.Annotated[dict[str, int], anno]]
        disassembled = Disassembled.create(provided)
        assert disassembled.original is provided
        assert disassembled.optional is True
        assert disassembled.optional_outer is True
        assert disassembled.optional_inner is False
        assert disassembled.extracted == dict[str, int]
        assert disassembled.origin_or_type == dict
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

    it "works on an attrs class":

        @define
        class Thing:
            one: int
            two: str

        provided = Thing
        disassembled = Disassembled.create(provided)
        assert disassembled.original is provided
        assert disassembled.optional is False
        assert disassembled.extracted == Thing
        assert disassembled.origin_or_type == Thing
        assert disassembled.checkable == Thing and isinstance(
            disassembled.checkable, InstanceCheckMeta
        )
        assert disassembled.annotation is None
        assert not disassembled.is_annotated
        assert disassembled.annotated is None
        assert disassembled.without_annotation == Thing
        assert disassembled.without_optional == Thing
        assert disassembled.fields == [
            Field(name="one", type=int),
            Field(name="two", type=str),
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
        assert not Disassembled.create(Child).is_equivalent_type_for(Thing(one=1, two="two"))

    it "works on an dataclasses class":

        @dataclass
        class Thing:
            one: int
            two: str

        provided = Thing
        disassembled = Disassembled.create(provided)
        assert disassembled.original is provided
        assert disassembled.optional is False
        assert disassembled.extracted == Thing
        assert disassembled.origin_or_type == Thing
        assert disassembled.checkable == Thing and isinstance(
            disassembled.checkable, InstanceCheckMeta
        )
        assert disassembled.annotation is None
        assert not disassembled.is_annotated
        assert disassembled.annotated is None
        assert disassembled.without_annotation == Thing
        assert disassembled.without_optional == Thing
        assert disassembled.fields == [
            Field(name="one", type=int),
            Field(name="two", type=str),
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
        assert not Disassembled.create(Child).is_equivalent_type_for(Thing(one=1, two="two"))

    it "works on a normal class":

        class Thing:
            def __init__(self, one: int, two: str):
                self.one = one
                self.two = two

        provided = Thing
        disassembled = Disassembled.create(provided)
        assert disassembled.original is provided
        assert disassembled.optional is False
        assert disassembled.extracted == Thing
        assert disassembled.origin_or_type == Thing
        assert disassembled.checkable == Thing and isinstance(
            disassembled.checkable, InstanceCheckMeta
        )
        assert disassembled.annotation is None
        assert not disassembled.is_annotated
        assert disassembled.annotated is None
        assert disassembled.without_annotation == Thing
        assert disassembled.without_optional == Thing
        assert disassembled.fields == [
            Field(name="one", type=int),
            Field(name="two", type=str),
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
        assert not Disassembled.create(Child).is_equivalent_type_for(Thing(one=1, two="two"))

    it "works on an annotated class":

        @define
        class Thing:
            one: int
            two: str

        anno = "blah"

        provided = tp.Annotated[Thing, anno]
        disassembled = Disassembled.create(provided)
        assert disassembled.original is provided
        assert disassembled.optional is False
        assert disassembled.extracted == Thing
        assert disassembled.origin_or_type == Thing
        assert disassembled.checkable == Thing and isinstance(
            disassembled.checkable, InstanceCheckMeta
        )
        assert disassembled.annotation is anno
        assert disassembled.is_annotated
        assert disassembled.annotated is provided
        assert disassembled.without_annotation == Thing
        assert disassembled.without_optional == tp.Annotated[Thing, anno]
        assert disassembled.fields == [
            Field(name="one", type=int),
            Field(name="two", type=str),
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
        assert not Disassembled.create(Child).is_equivalent_type_for(Thing(one=1, two="two"))

    it "works on an optional annotated class":

        @dataclass
        class Thing:
            one: int
            two: str

        anno = "blah"

        provided = tp.Annotated[tp.Optional[Thing], anno]
        disassembled = Disassembled.create(provided)
        assert disassembled.original is provided
        assert disassembled.optional is True
        assert disassembled.optional_outer is False
        assert disassembled.optional_inner is True
        assert disassembled.extracted == Thing
        assert disassembled.origin_or_type == Thing
        assert disassembled.checkable == Thing and isinstance(
            disassembled.checkable, InstanceCheckMeta
        )
        assert disassembled.annotation is anno
        assert disassembled.is_annotated
        assert disassembled.annotated is provided
        assert disassembled.without_annotation == Thing | None
        assert disassembled.without_optional == tp.Annotated[Thing, anno]
        assert disassembled.fields == [
            Field(name="one", type=int),
            Field(name="two", type=str),
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
        assert not Disassembled.create(Child).is_equivalent_type_for(Thing(one=1, two="two"))

    it "works on an optional annotated generic class":

        @dataclass
        class Thing(tp.Generic[T, U]):
            one: T
            two: U

        anno = "blah"

        provided = tp.Annotated[tp.Optional[Thing[int, str]], anno]
        disassembled = Disassembled.create(provided)
        assert disassembled.original is provided
        assert disassembled.optional is True
        assert disassembled.optional_outer is False
        assert disassembled.optional_inner is True
        assert disassembled.extracted == Thing[int, str]
        assert disassembled.origin_or_type == Thing
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
            Field(name="one", type=int),
            Field(name="two", type=str),
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
        assert not Disassembled.create(Child).is_equivalent_type_for(Thing(one=1, two="two"))

    it "works on an optional annotated generic class without concrete types":

        @define
        class Thing(tp.Generic[T, U]):
            one: T
            two: U

        anno = "blah"

        provided = tp.Annotated[tp.Optional[Thing], anno]
        disassembled = Disassembled.create(provided)
        assert disassembled.original is provided
        assert disassembled.optional is True
        assert disassembled.optional_outer is False
        assert disassembled.optional_inner is True
        assert disassembled.extracted == Thing
        assert disassembled.origin_or_type == Thing
        assert disassembled.checkable == Thing and isinstance(
            disassembled.checkable, InstanceCheckMeta
        )
        assert disassembled.annotation is anno
        assert disassembled.is_annotated
        assert disassembled.annotated is provided
        assert disassembled.without_annotation == Thing | None
        assert disassembled.without_optional == tp.Annotated[Thing, anno]
        assert disassembled.fields == [
            Field(name="one", type=object),
            Field(name="two", type=object),
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
        assert not Disassembled.create(Child).is_equivalent_type_for(Thing(one=1, two="two"))

describe "getting fields":
    it "works when there is a chain":

        @define
        class Stuff:
            thing: "Thing"

        @define
        class Thing:
            stuff: tp.Optional["Stuff"]

        resolve_types(Thing, globals(), locals())

        disassembled = Disassembled.create(Thing)
        assert disassembled.fields == [Field(name="stuff", type=Stuff | None)]

    it "works on normal class":

        class Thing:
            def __init__(self, one: int, /, two: str, *, three: bool = False, **kwargs):
                pass

        disassembled = Disassembled.create(Thing)
        assert disassembled.fields_getter is fields_from_class
        assert disassembled.fields_from is Thing
        assertParams(
            disassembled.fields,
            [
                Field(name="one", kind=inspect.Parameter.POSITIONAL_ONLY, type=int),
                Field(name="two", kind=inspect.Parameter.POSITIONAL_OR_KEYWORD, type=str),
                Field(
                    name="three",
                    kind=inspect.Parameter.KEYWORD_ONLY,
                    type=bool,
                    default=Default(False),
                ),
                Field(name="", kind=inspect.Parameter.VAR_KEYWORD, type=object),
            ],
        )

    it "works on attrs class":

        @define
        class Thing:
            one: int
            two: str = "one"
            three: bool = attrs.field(kw_only=True, default=False)

        disassembled = Disassembled.create(Thing)
        assert disassembled.fields_getter is fields_from_attrs
        assert disassembled.fields_from is Thing
        assertParams(
            disassembled.fields,
            [
                Field(name="one", kind=inspect.Parameter.POSITIONAL_OR_KEYWORD, type=int),
                Field(
                    name="two",
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    type=str,
                    default=Default("one"),
                ),
                Field(
                    name="three",
                    kind=inspect.Parameter.KEYWORD_ONLY,
                    type=bool,
                    default=Default(False),
                ),
            ],
        )

    it "works on dataclasses class":

        @dataclass
        class Thing:
            one: int
            two: str = "one"
            three: bool = dataclasses.field(kw_only=True, default=False)

        disassembled = Disassembled.create(Thing)
        assert disassembled.fields_getter is fields_from_dataclasses
        assert disassembled.fields_from is Thing
        assertParams(
            disassembled.fields,
            [
                Field(name="one", kind=inspect.Parameter.POSITIONAL_OR_KEYWORD, type=int),
                Field(
                    name="two",
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    type=str,
                    default=Default("one"),
                ),
                Field(
                    name="three",
                    kind=inspect.Parameter.KEYWORD_ONLY,
                    type=bool,
                    default=Default(False),
                ),
            ],
        )

describe "checkable":
    it "can find instances and subclasses of basic types":
        db = Disassembled.create(int)
        assert isinstance(23, db.checkable)
        assert not isinstance(23.4, db.checkable)
        assert not isinstance("asdf", db.checkable)
        assert not isinstance({}, db.checkable)

        class MyInt(int):
            pass

        assert issubclass(int, db.checkable)
        assert issubclass(MyInt, db.checkable)
        assert issubclass(Disassembled.create(MyInt).checkable, db.checkable)

        class NotMyInt:
            pass

        assert not issubclass(NotMyInt, db.checkable)
        assert not issubclass(Disassembled.create(NotMyInt).checkable, db.checkable)
        assert not issubclass(float, db.checkable)
        assert not issubclass(dict, db.checkable)

        assert isinstance(db.checkable, InstanceCheckMeta)
        assert isinstance(db.checkable, type)
        assert isinstance(db.checkable, Disassembled.create(type).checkable)

        assert issubclass(db.checkable, InstanceCheck)
        assert not issubclass(db.checkable, type)
        assert not issubclass(type, db.checkable)
        assert not issubclass(Disassembled.create(type).checkable, db.checkable)
        assert not issubclass(db.checkable, Disassembled.create(type).checkable)
        assert not isinstance(db.checkable, int)
        assert not isinstance(db.checkable, Disassembled.create(int).checkable)
        assert not issubclass(db.checkable, NotMyInt)
        assert not issubclass(db.checkable, Disassembled.create(NotMyInt).checkable)

        assert db.checkable.Meta.typ == int
        assert db.checkable.Meta.original == int
        assert not db.checkable.Meta.optional
        assert db.checkable.Meta.without_optional == int
        assert db.checkable.Meta.without_annotation == int

    it "can find instances and subclasses of union types":
        db = Disassembled.create(int | str)
        assert isinstance(23, db.checkable)
        assert not isinstance(23.4, db.checkable)
        assert isinstance("asdf", db.checkable)
        assert not isinstance({}, db.checkable)

        class MyInt(int):
            pass

        assert issubclass(MyInt, db.checkable)
        assert issubclass(int, db.checkable)
        assert issubclass(Disassembled.create(MyInt).checkable, db.checkable)

        class MyString(str):
            pass

        assert issubclass(str, db.checkable)
        assert issubclass(MyString, db.checkable)
        assert issubclass(Disassembled.create(MyString).checkable, db.checkable)

        class NotMyInt:
            pass

        assert not issubclass(NotMyInt, db.checkable)
        assert not issubclass(Disassembled.create(NotMyInt).checkable, db.checkable)
        assert not issubclass(float, db.checkable)
        assert not issubclass(dict, db.checkable)

        assert isinstance(db.checkable, InstanceCheckMeta)
        assert isinstance(db.checkable, type)
        assert isinstance(db.checkable, Disassembled.create(type).checkable)

        assert issubclass(db.checkable, InstanceCheck)
        assert not issubclass(db.checkable, type)
        assert not issubclass(type, db.checkable)
        assert not issubclass(Disassembled.create(type).checkable, db.checkable)
        assert not issubclass(db.checkable, Disassembled.create(type).checkable)
        assert not isinstance(db.checkable, int)
        assert not isinstance(db.checkable, Disassembled.create(int).checkable)
        assert not issubclass(db.checkable, NotMyInt)
        assert not issubclass(db.checkable, str)
        assert not issubclass(db.checkable, Disassembled.create(NotMyInt).checkable)

        assert db.checkable.Meta.typ == int | str
        assert db.checkable.Meta.original == int | str
        assert not db.checkable.Meta.optional
        assert db.checkable.Meta.without_optional == int | str
        assert db.checkable.Meta.without_annotation == int | str

    it "can find instances and subclasses of complicated union type":
        provided = tp.Union[tp.Annotated[list[int], "str"], tp.Annotated[int | str | None, "hello"]]
        db = Disassembled.create(provided)
        assert isinstance(23, db.checkable)
        assert not isinstance(23.4, db.checkable)
        assert isinstance("asdf", db.checkable)
        assert not isinstance({}, db.checkable)

        class MyInt(int):
            pass

        assert issubclass(MyInt, db.checkable)
        assert issubclass(int, db.checkable)
        assert issubclass(Disassembled.create(MyInt).checkable, db.checkable)

        class MyString(str):
            pass

        assert issubclass(str, db.checkable)
        assert issubclass(MyString, db.checkable)
        assert issubclass(Disassembled.create(MyString).checkable, db.checkable)

        class NotMyInt:
            pass

        assert not issubclass(NotMyInt, db.checkable)
        assert not issubclass(Disassembled.create(NotMyInt).checkable, db.checkable)
        assert not issubclass(float, db.checkable)
        assert not issubclass(dict, db.checkable)

        assert isinstance(db.checkable, InstanceCheckMeta)
        assert isinstance(db.checkable, type)
        assert isinstance(db.checkable, Disassembled.create(type).checkable)

        assert issubclass(db.checkable, InstanceCheck)
        assert not issubclass(db.checkable, type)
        assert not issubclass(type, db.checkable)
        assert not issubclass(Disassembled.create(type).checkable, db.checkable)
        assert not issubclass(db.checkable, Disassembled.create(type).checkable)
        assert not isinstance(db.checkable, int)
        assert not isinstance(db.checkable, Disassembled.create(int).checkable)
        assert not issubclass(db.checkable, NotMyInt)
        assert not issubclass(db.checkable, str)
        assert not issubclass(db.checkable, Disassembled.create(NotMyInt).checkable)

        assert db.checkable.Meta.typ == provided
        assert db.checkable.Meta.original == provided
        assert not db.checkable.Meta.optional
        assert db.checkable.Meta.without_optional == provided
        assert db.checkable.Meta.without_annotation == provided

    it "can find instances and subclasses of optional basic types":
        db = Disassembled.create(int | None)
        assert isinstance(23, db.checkable)
        assert isinstance(None, db.checkable)
        assert not isinstance(23.4, db.checkable)
        assert not isinstance("asdf", db.checkable)

        class MyInt(int):
            pass

        assert issubclass(MyInt, db.checkable)
        assert issubclass(Disassembled.create(MyInt).checkable, db.checkable)

        class NotMyInt:
            pass

        assert not issubclass(NotMyInt, db.checkable)
        assert not issubclass(Disassembled.create(NotMyInt).checkable, db.checkable)

        assert isinstance(db.checkable, InstanceCheckMeta)
        assert isinstance(db.checkable, type)
        assert isinstance(db.checkable, Disassembled.create(type).checkable)

        assert issubclass(db.checkable, InstanceCheck)
        assert not issubclass(db.checkable, type)
        assert not issubclass(type, db.checkable)
        assert not issubclass(Disassembled.create(type).checkable, db.checkable)
        assert not issubclass(db.checkable, Disassembled.create(type).checkable)
        assert not isinstance(db.checkable, int)
        assert not isinstance(db.checkable, Disassembled.create(int).checkable)
        assert not issubclass(db.checkable, NotMyInt)
        assert not issubclass(db.checkable, Disassembled.create(NotMyInt).checkable)

        assert db.checkable.Meta.typ == int
        assert db.checkable.Meta.original == int | None
        assert db.checkable.Meta.optional
        assert db.checkable.Meta.without_optional == int
        assert db.checkable.Meta.without_annotation == int | None

    it "can find instances and subclasses of annotated types":
        db = Disassembled.create(tp.Annotated[int | None, "stuff"])
        assert isinstance(23, db.checkable)
        assert isinstance(None, db.checkable)
        assert not isinstance(23.4, db.checkable)
        assert not isinstance("asdf", db.checkable)

        class MyInt(int):
            pass

        assert issubclass(MyInt, db.checkable)
        assert issubclass(Disassembled.create(MyInt).checkable, db.checkable)

        class NotMyInt:
            pass

        assert not issubclass(NotMyInt, db.checkable)
        assert not issubclass(Disassembled.create(NotMyInt).checkable, db.checkable)

        assert isinstance(db.checkable, InstanceCheckMeta)
        assert isinstance(db.checkable, type)
        assert isinstance(db.checkable, Disassembled.create(type).checkable)

        assert issubclass(db.checkable, InstanceCheck)
        assert not issubclass(db.checkable, type)
        assert not issubclass(type, db.checkable)
        assert not issubclass(Disassembled.create(type).checkable, db.checkable)
        assert not issubclass(db.checkable, Disassembled.create(type).checkable)
        assert not isinstance(db.checkable, int)
        assert not isinstance(db.checkable, Disassembled.create(int).checkable)
        assert not issubclass(db.checkable, NotMyInt)
        assert not issubclass(db.checkable, Disassembled.create(NotMyInt).checkable)

        assert db.checkable.Meta.typ == int
        assert db.checkable.Meta.original == tp.Annotated[int | None, "stuff"]
        assert db.checkable.Meta.optional
        assert db.checkable.Meta.without_optional == tp.Annotated[int, "stuff"]
        assert db.checkable.Meta.without_annotation == int | None

    it "can find instances and subclasses of user defined classes":

        class Mine:
            pass

        db = Disassembled.create(Mine)
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
        assert isinstance(db.checkable, Disassembled.create(type).checkable)

        assert issubclass(db.checkable, InstanceCheck)
        assert not issubclass(db.checkable, type)
        assert not issubclass(type, db.checkable)
        assert not issubclass(Disassembled.create(type).checkable, db.checkable)
        assert not issubclass(db.checkable, Disassembled.create(type).checkable)
        assert not isinstance(db.checkable, int)
        assert not isinstance(db.checkable, Disassembled.create(int).checkable)
        assert not issubclass(db.checkable, Other)
        assert not issubclass(db.checkable, Disassembled.create(Other).checkable)

        assert db.checkable.Meta.typ == Mine
        assert db.checkable.Meta.original == Mine
        assert not db.checkable.Meta.optional
        assert db.checkable.Meta.without_optional == Mine
        assert db.checkable.Meta.without_annotation == Mine

    it "can instantiate the provided type":
        checkable = Disassembled.create(dict[str, bool]).checkable
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

        checkable = Disassembled.create(Thing).checkable
        made = tp.cast(tp.Callable, checkable)(one=1)
        assert isinstance(made, Thing)
        assert made.one == 1

        assert checkable.Meta.typ == Thing
        assert checkable.Meta.original == Thing
        assert not checkable.Meta.optional
        assert checkable.Meta.without_optional == Thing
        assert checkable.Meta.without_annotation == Thing

        constructor: tp.Callable = Disassembled.create(int | str).checkable
        with pytest.raises(ValueError, match="Cannot instantiate a union type"):
            constructor(1)

    it "can get typing origin":

        assert tp.get_origin(Disassembled.create(str | int).checkable) == types.UnionType
        assert tp.get_origin(Disassembled.create(dict[str, int]).checkable) == dict
        assert tp.get_origin(Disassembled.create(dict[str, int] | None).checkable) == dict
        assert (
            tp.get_origin(Disassembled.create(tp.Annotated[dict[str, int] | None, "hi"]).checkable)
            == dict
        )

        assert tp.get_origin(Disassembled.create(dict).checkable) is None
        assert tp.get_origin(Disassembled.create(dict | None).checkable) is None
        assert tp.get_origin(Disassembled.create(tp.Annotated[dict | None, "hi"]).checkable) is None

        assert tp.get_origin(Disassembled.create(dict | str).checkable) is types.UnionType

        class Thing(tp.Generic[T]):
            pass

        assert tp.get_origin(Disassembled.create(Thing).checkable) is None
        assert tp.get_origin(Disassembled.create(Thing[int]).checkable) is Thing

    it "can get typing args":

        assert tp.get_args(Disassembled.create(str | int).checkable) == (str, int)
        assert tp.get_args(Disassembled.create(dict[str, int]).checkable) == (str, int)
        assert tp.get_args(Disassembled.create(dict[str, int] | None).checkable) == (str, int)
        assert tp.get_args(
            Disassembled.create(tp.Annotated[dict[str, int] | None, "hi"]).checkable
        ) == (str, int)

        assert tp.get_args(Disassembled.create(dict).checkable) == ()
        assert tp.get_args(Disassembled.create(dict | None).checkable) == ()
        assert tp.get_args(Disassembled.create(tp.Annotated[dict | None, "hi"]).checkable) == ()

        assert tp.get_args(Disassembled.create(dict | str).checkable) == (dict, str)

        class Thing(tp.Generic[T]):
            pass

        assert tp.get_args(Disassembled.create(Thing).checkable) == ()
        assert tp.get_args(Disassembled.create(Thing[int]).checkable) == (int,)
