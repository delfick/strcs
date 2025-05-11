import copy
import dataclasses
import types
import typing
from collections.abc import Callable
from typing import Annotated, Generic, NewType, TypeVar, Union

import attrs
import pytest

import strcs

Disassembler = strcs.disassemble.Disassembler


T = TypeVar("T")


class TestInstanceCheck:
    def test_it_can_find_instances_and_subclasses_of_basic_types(self, Dis: Disassembler):
        db = Dis(int)
        assert isinstance(23, db.checkable)
        assert not isinstance(23.4, db.checkable)
        assert not isinstance("asdf", db.checkable)
        assert not isinstance({}, db.checkable)

        class MyInt(int):
            pass

        assert issubclass(int, db.checkable)
        assert issubclass(MyInt, db.checkable)
        assert issubclass(Dis(MyInt).checkable, db.checkable)

        class NotMyInt:
            pass

        assert not issubclass(NotMyInt, db.checkable)
        assert not issubclass(Dis(NotMyInt).checkable, db.checkable)
        assert not issubclass(float, db.checkable)
        assert not issubclass(dict, db.checkable)

        assert isinstance(db.checkable, strcs.InstanceCheckMeta)
        assert isinstance(db.checkable, type)
        assert isinstance(db.checkable, Dis(type).checkable)

        assert issubclass(db.checkable, strcs.InstanceCheck)
        assert not issubclass(db.checkable, type)
        assert not issubclass(type, db.checkable)
        assert not issubclass(Dis(type).checkable, db.checkable)
        assert not issubclass(db.checkable, Dis(type).checkable)
        assert not isinstance(db.checkable, int)
        assert not isinstance(db.checkable, Dis(int).checkable)
        assert not issubclass(db.checkable, NotMyInt)
        assert not issubclass(db.checkable, Dis(NotMyInt).checkable)

        assert db.checkable.Meta.typ == int
        assert db.checkable.Meta.original == int
        assert not db.checkable.Meta.optional
        assert db.checkable.Meta.without_optional == int
        assert db.checkable.Meta.without_annotation == int

    def test_it_can_find_instances_and_subclasses_of_union_types(self, Dis: Disassembler):
        db = Dis(int | str)
        assert isinstance(23, db.checkable)
        assert not isinstance(23.4, db.checkable)
        assert isinstance("asdf", db.checkable)
        assert not isinstance({}, db.checkable)

        class MyInt(int):
            pass

        assert issubclass(MyInt, db.checkable)
        assert issubclass(int, db.checkable)
        assert issubclass(Dis(MyInt).checkable, db.checkable)

        class MyString(str):
            pass

        assert issubclass(str, db.checkable)
        assert issubclass(MyString, db.checkable)
        assert issubclass(Dis(MyString).checkable, db.checkable)

        class NotMyInt:
            pass

        assert not issubclass(NotMyInt, db.checkable)
        assert not issubclass(Dis(NotMyInt).checkable, db.checkable)
        assert not issubclass(float, db.checkable)
        assert not issubclass(dict, db.checkable)

        assert isinstance(db.checkable, strcs.InstanceCheckMeta)
        assert isinstance(db.checkable, type)
        assert isinstance(db.checkable, Dis(type).checkable)

        assert issubclass(db.checkable, strcs.InstanceCheck)
        assert not issubclass(db.checkable, type)
        assert not issubclass(type, db.checkable)
        assert not issubclass(Dis(type).checkable, db.checkable)
        assert not issubclass(db.checkable, Dis(type).checkable)
        assert not isinstance(db.checkable, int)
        assert not isinstance(db.checkable, Dis(int).checkable)
        assert not issubclass(db.checkable, NotMyInt)
        assert not issubclass(db.checkable, str)
        assert not issubclass(db.checkable, Dis(NotMyInt).checkable)

        assert db.checkable.Meta.typ == int | str
        assert db.checkable.Meta.original == int | str
        assert not db.checkable.Meta.optional
        assert db.checkable.Meta.without_optional == int | str
        assert db.checkable.Meta.without_annotation == int | str

    def test_it_can_find_instances_and_subclasses_of_complicated_union_type(
        self, Dis: Disassembler
    ):
        provided = Union[Annotated[list[int], "str"], Annotated[int | str | None, "hello"]]
        db = Dis(provided)
        assert isinstance(23, db.checkable)
        assert not isinstance(23.4, db.checkable)
        assert isinstance("asdf", db.checkable)
        assert not isinstance({}, db.checkable)

        class MyInt(int):
            pass

        assert issubclass(MyInt, db.checkable)
        assert issubclass(int, db.checkable)
        assert issubclass(Dis(MyInt).checkable, db.checkable)

        class MyString(str):
            pass

        assert issubclass(str, db.checkable)
        assert issubclass(MyString, db.checkable)
        assert issubclass(Dis(MyString).checkable, db.checkable)

        class NotMyInt:
            pass

        assert not issubclass(NotMyInt, db.checkable)
        assert not issubclass(Dis(NotMyInt).checkable, db.checkable)
        assert not issubclass(float, db.checkable)
        assert not issubclass(dict, db.checkable)

        assert isinstance(db.checkable, strcs.InstanceCheckMeta)
        assert isinstance(db.checkable, type)
        assert isinstance(db.checkable, Dis(type).checkable)

        assert issubclass(db.checkable, strcs.InstanceCheck)
        assert not issubclass(db.checkable, type)
        assert not issubclass(type, db.checkable)
        assert not issubclass(Dis(type).checkable, db.checkable)
        assert not issubclass(db.checkable, Dis(type).checkable)
        assert not isinstance(db.checkable, int)
        assert not isinstance(db.checkable, Dis(int).checkable)
        assert not issubclass(db.checkable, NotMyInt)
        assert not issubclass(db.checkable, str)
        assert not issubclass(db.checkable, Dis(NotMyInt).checkable)

        assert db.checkable.Meta.typ == provided
        assert db.checkable.Meta.original == provided
        assert not db.checkable.Meta.optional
        assert db.checkable.Meta.without_optional == provided
        assert db.checkable.Meta.without_annotation == provided

    def test_it_can_find_instances_and_subclasses_of_optional_basic_types(self, Dis: Disassembler):
        db = Dis(int | None)
        assert isinstance(23, db.checkable)
        assert isinstance(None, db.checkable)
        assert not isinstance(23.4, db.checkable)
        assert not isinstance("asdf", db.checkable)

        class MyInt(int):
            pass

        assert issubclass(MyInt, db.checkable)
        assert issubclass(Dis(MyInt).checkable, db.checkable)

        class NotMyInt:
            pass

        assert not issubclass(NotMyInt, db.checkable)
        assert not issubclass(Dis(NotMyInt).checkable, db.checkable)

        assert isinstance(db.checkable, strcs.InstanceCheckMeta)
        assert isinstance(db.checkable, type)
        assert isinstance(db.checkable, Dis(type).checkable)

        assert issubclass(db.checkable, strcs.InstanceCheck)
        assert not issubclass(db.checkable, type)
        assert not issubclass(type, db.checkable)
        assert not issubclass(Dis(type).checkable, db.checkable)
        assert not issubclass(db.checkable, Dis(type).checkable)
        assert not isinstance(db.checkable, int)
        assert not isinstance(db.checkable, Dis(int).checkable)
        assert not issubclass(db.checkable, NotMyInt)
        assert not issubclass(db.checkable, Dis(NotMyInt).checkable)

        assert db.checkable.Meta.typ == int | None
        assert db.checkable.Meta.original == int | None
        assert db.checkable.Meta.optional
        assert db.checkable.Meta.without_optional == int
        assert db.checkable.Meta.without_annotation == int | None

    def test_it_can_find_instances_and_subclasses_of_annotated_types(self, Dis: Disassembler):
        db = Dis(Annotated[int | None, "stuff"])
        assert isinstance(23, db.checkable)
        assert isinstance(None, db.checkable)
        assert not isinstance(23.4, db.checkable)
        assert not isinstance("asdf", db.checkable)

        class MyInt(int):
            pass

        assert issubclass(MyInt, db.checkable)
        assert issubclass(Dis(MyInt).checkable, db.checkable)

        class NotMyInt:
            pass

        assert not issubclass(NotMyInt, db.checkable)
        assert not issubclass(Dis(NotMyInt).checkable, db.checkable)

        assert isinstance(db.checkable, strcs.InstanceCheckMeta)
        assert isinstance(db.checkable, type)
        assert isinstance(db.checkable, Dis(type).checkable)

        assert issubclass(db.checkable, strcs.InstanceCheck)
        assert not issubclass(db.checkable, type)
        assert not issubclass(type, db.checkable)
        assert not issubclass(Dis(type).checkable, db.checkable)
        assert not issubclass(db.checkable, Dis(type).checkable)
        assert not isinstance(db.checkable, int)
        assert not isinstance(db.checkable, Dis(int).checkable)
        assert not issubclass(db.checkable, NotMyInt)
        assert not issubclass(db.checkable, Dis(NotMyInt).checkable)

        assert db.checkable.Meta.typ == int | None
        assert db.checkable.Meta.original == Annotated[int | None, "stuff"]
        assert db.checkable.Meta.optional
        assert db.checkable.Meta.without_optional == Annotated[int, "stuff"]
        assert db.checkable.Meta.without_annotation == int | None

    def test_it_can_find_instances_and_subclasses_of_user_defined_classes(self, Dis: Disassembler):
        class Mine:
            pass

        db = Dis(Mine)
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

        assert isinstance(db.checkable, strcs.InstanceCheckMeta)
        assert isinstance(db.checkable, type)
        assert isinstance(db.checkable, Dis(type).checkable)

        assert issubclass(db.checkable, strcs.InstanceCheck)
        assert not issubclass(db.checkable, type)
        assert not issubclass(type, db.checkable)
        assert not issubclass(Dis(type).checkable, db.checkable)
        assert not issubclass(db.checkable, Dis(type).checkable)
        assert not isinstance(db.checkable, int)
        assert not isinstance(db.checkable, Dis(int).checkable)
        assert not issubclass(db.checkable, Other)
        assert not issubclass(db.checkable, Dis(Other).checkable)

        assert db.checkable.Meta.typ == Mine
        assert db.checkable.Meta.original == Mine
        assert not db.checkable.Meta.optional
        assert db.checkable.Meta.without_optional == Mine
        assert db.checkable.Meta.without_annotation == Mine

    def test_it_can_find_instances_and_subclasses_of_NewType_objects(self, Dis: Disassembler):
        class Mine:
            pass

        MineT = NewType("MineT", Mine)

        db = Dis(MineT)
        assert not isinstance(23, db.checkable)
        assert not isinstance(23.4, db.checkable)
        assert not isinstance("asdf", db.checkable)
        assert isinstance(Mine(), db.checkable)

        assert db == Mine
        assert db == MineT

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

        assert isinstance(db.checkable, strcs.InstanceCheckMeta)
        assert isinstance(db.checkable, type)
        assert isinstance(db.checkable, Dis(type).checkable)

        assert issubclass(db.checkable, strcs.InstanceCheck)
        assert not issubclass(db.checkable, type)
        assert not issubclass(type, db.checkable)
        assert not issubclass(Dis(type).checkable, db.checkable)
        assert not issubclass(db.checkable, Dis(type).checkable)
        assert not isinstance(db.checkable, int)
        assert not isinstance(db.checkable, Dis(int).checkable)
        assert not issubclass(db.checkable, Other)
        assert not issubclass(db.checkable, Dis(Other).checkable)

        assert db.checkable.Meta.typ == MineT
        assert db.checkable.Meta.original == MineT
        assert not db.checkable.Meta.optional
        assert db.checkable.Meta.without_optional == MineT
        assert db.checkable.Meta.without_annotation == MineT

    def test_it_can_find_instances_and_subclasses_of_primtive_NewType_objects(
        self, Dis: Disassembler
    ):
        MyInt = NewType("MyInt", int)

        db = Dis(MyInt)
        assert isinstance(23, db.checkable)
        assert not isinstance(23.4, db.checkable)
        assert not isinstance("asdf", db.checkable)

        assert db.checkable == MyInt
        assert db.checkable == int

        assert isinstance(db.checkable, strcs.InstanceCheckMeta)
        assert isinstance(db.checkable, type)
        assert isinstance(db.checkable, Dis(type).checkable)
        assert not isinstance(db.checkable, int)
        assert not isinstance(db.checkable, Dis(int).checkable)

        assert issubclass(db.checkable, strcs.InstanceCheck)
        assert issubclass(db.checkable, Dis(MyInt).checkable)
        assert not issubclass(db.checkable, type)
        assert not issubclass(type, db.checkable)
        assert not issubclass(Dis(type).checkable, db.checkable)
        assert not issubclass(db.checkable, Dis(type).checkable)
        assert not issubclass(db.checkable, str)
        assert not issubclass(db.checkable, Dis(str).checkable)

        assert db.checkable.Meta.typ == MyInt
        assert db.checkable.Meta.original == MyInt
        assert not db.checkable.Meta.optional
        assert db.checkable.Meta.without_optional == MyInt
        assert db.checkable.Meta.without_annotation == MyInt

    def test_it_can_instantiate_the_provided_type(self, Dis: Disassembler):
        checkable = Dis(dict[str, bool]).checkable
        made = checkable([("1", True), ("2", False)])  # type: ignore[call-arg]
        assert made == {"1": True, "2": False}

        assert checkable.Meta.typ == dict
        assert checkable.Meta.original == dict[str, bool]
        assert not checkable.Meta.optional
        assert checkable.Meta.without_optional == dict[str, bool]
        assert checkable.Meta.without_annotation == dict[str, bool]

        class Thing:
            def __init__(self, one: int):
                self.one = one

        checkable = Dis(Thing).checkable
        made = checkable(one=1)  # type: ignore[call-arg]
        assert isinstance(made, Thing)
        assert made.one == 1

        assert checkable.Meta.typ == Thing
        assert checkable.Meta.original == Thing
        assert not checkable.Meta.optional
        assert checkable.Meta.without_optional == Thing
        assert checkable.Meta.without_annotation == Thing

        constructor: Callable = Dis(int | str).checkable
        with pytest.raises(ValueError, match="Cannot instantiate this type"):
            constructor(1)

    def test_it_can_get_repr(self, Dis: Disassembler):
        class One:
            one: int
            two: str

        class Two(Generic[T]):
            one: T
            two: str

        @attrs.define
        class Three:
            one: bool
            two: dict[str, One]

        examples = [
            (0, repr(int)),
            (1, repr(int)),
            (None, repr(None)),
            (True, repr(bool)),
            (False, repr(bool)),
            ([], repr(list)),
            ({}, repr(dict)),
            ([1], repr(list)),
            ({2: 1}, repr(dict)),
            (One, repr(One)),
            (Two, repr(Two)),
            (Two[int], repr(Two)),
            (Three, repr(Three)),
            (int | str, f"{int!r} | {str!r}"),
            (int | None, f"{int!r} | {type(None)!r}"),
            (Union[int, str], f"{int!r} | {str!r}"),
            (Union[bool, None], f"{bool!r} | {type(None)!r}"),
            (One | int, f"{One!r} | {int!r}"),
        ]
        for thing, expected in examples:
            checkable = Dis(thing).checkable
            assert repr(checkable) == expected

    def test_it_can_get_typing_origin(self, Dis: Disassembler):
        assert typing.get_origin(Dis(str | int).checkable) == types.UnionType
        assert typing.get_origin(Dis(dict[str, int]).checkable) == dict
        assert typing.get_origin(Dis(dict[str, int] | None).checkable) == types.UnionType
        assert (
            typing.get_origin(Dis(Annotated[dict[str, int] | None, "hi"]).checkable)
            == types.UnionType
        )

        assert typing.get_origin(Dis(dict).checkable) is None
        assert typing.get_origin(Dis(dict | None).checkable) is types.UnionType
        assert typing.get_origin(Dis(Annotated[dict | None, "hi"]).checkable) is types.UnionType

        assert typing.get_origin(Dis(dict | str).checkable) is types.UnionType

        class Thing(Generic[T]):
            pass

        assert typing.get_origin(Dis(Thing).checkable) is None
        assert typing.get_origin(Dis(Thing[int]).checkable) is Thing

    def test_it_can_get_typing_args(self, Dis: Disassembler):
        assert typing.get_args(Dis(str | int).checkable) == (str, int)
        assert typing.get_args(Dis(dict[str, int]).checkable) == (str, int)
        assert typing.get_args(Dis(dict[str, int] | None).checkable) == (
            dict[str, int],
            type(None),
        )
        assert typing.get_args(Dis(Annotated[dict[str, int] | None, "hi"]).checkable) == (
            dict[str, int],
            type(None),
        )

        assert typing.get_args(Dis(dict).checkable) == ()
        assert typing.get_args(Dis(dict | None).checkable) == (
            dict,
            type(None),
        )
        assert typing.get_args(Dis(Annotated[dict | None, "hi"]).checkable) == (dict, type(None))

        assert typing.get_args(Dis(dict | str).checkable) == (dict, str)

        class Thing(Generic[T]):
            pass

        assert typing.get_args(Dis(Thing).checkable) == ()
        assert typing.get_args(Dis(Thing[int]).checkable) == (int,)

    def test_it_can_get_typing_hints(self, Dis: Disassembler):
        assert typing.get_type_hints(Dis(int).checkable) == {}

        class Thing:
            one: int
            two: str

        class Other(Generic[T]):
            one: T
            two: str

        @attrs.define
        class Stuff:
            one: bool
            two: dict[str, Thing]

        lcls = copy.copy(locals())
        lcls["TypeCache"] = strcs.TypeCache

        thing: object
        for thing in (0, 1, None, True, False, [], {}, Thing, Other, Other[int], Stuff):
            want_result: object | None = None
            want_error: Exception | None = None

            got_result: object | None = None
            got_error: Exception | None = None

            try:
                want_result = typing.get_type_hints(thing)
            except Exception as e:
                want_error = e

            try:
                got_result = typing.get_type_hints(Dis(thing).checkable)
            except Exception as e:
                got_error = e

            if want_result is None and isinstance(want_error, TypeError):
                # Can't get around the fact that checkable is a type
                assert got_result == {}
                assert got_error is None
            else:
                assert got_result == want_result, thing
                assert got_error == want_error, thing

    def test_it_allows_attrs_helpers(self, Dis: Disassembler):
        @attrs.define
        class One:
            one: int
            two: str

        @dataclasses.dataclass
        class Two:
            one: int
            two: str

        class Three:
            one: int
            two: str

        for kls in (One, Two, Three):
            checkable = Dis(kls).checkable
            is_attrs = attrs.has(kls)
            assert is_attrs == attrs.has(checkable)
            if is_attrs:
                assert attrs.fields(kls) == attrs.fields(checkable)  # type: ignore

    def test_it_allows_dataclasses_helpers(self, Dis: Disassembler):
        @attrs.define
        class One:
            one: int
            two: str

        @dataclasses.dataclass
        class Two:
            one: int
            two: str

        class Three:
            one: int
            two: str

        for kls in (One, Two, Three):
            checkable = Dis(kls).checkable
            is_dataclass = dataclasses.is_dataclass(kls)
            assert is_dataclass == dataclasses.is_dataclass(checkable)
            if is_dataclass:
                assert dataclasses.fields(kls) == dataclasses.fields(checkable)  # type: ignore[arg-type]

    def test_it_can_get_NewType_supertype(self, Dis: Disassembler):
        class Thing:
            pass

        Alias = NewType("Alias", Thing)

        checkable = Dis(Alias).checkable
        assert isinstance(checkable, NewType)
        assert checkable.__supertype__ is Thing
