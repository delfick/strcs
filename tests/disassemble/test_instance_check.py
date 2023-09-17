# coding: spec
import copy
import dataclasses
import types
import typing as tp

import attrs
import pytest

import strcs
from strcs import InstanceCheck, InstanceCheckMeta, Type


@pytest.fixture()
def type_cache() -> strcs.TypeCache:
    return strcs.TypeCache()


T = tp.TypeVar("T")

describe "InstanceCheck":
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

    it "can find instances and subclasses of NewType objects", type_cache: strcs.TypeCache:

        class Mine:
            pass

        MineT = tp.NewType("MineT", Mine)

        db = Type.create(MineT, expect=MineT, cache=type_cache)
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

        assert db.checkable.Meta.typ == MineT
        assert db.checkable.Meta.original == MineT
        assert not db.checkable.Meta.optional
        assert db.checkable.Meta.without_optional == MineT
        assert db.checkable.Meta.without_annotation == MineT

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

    it "can get repr", type_cache: strcs.TypeCache:

        class One:
            one: int
            two: str

        class Two(tp.Generic[T]):
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
            (int | str, f"{repr(int)} | {repr(str)}"),
            (int | None, repr(int)),
            (tp.Union[int, str], f"{repr(int)} | {repr(str)}"),
            (tp.Union[bool, None], repr(bool)),
            (One | int, f"{repr(One)} | {repr(int)}"),
        ]
        for thing, expected in examples:
            checkable = Type.create(thing, cache=type_cache).checkable
            assert repr(checkable) == expected

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

    it "can get typing hints", type_cache: strcs.TypeCache:
        assert tp.get_type_hints(Type.create(int, cache=type_cache).checkable) == {}

        class Thing:
            one: int
            two: str

        class Other(tp.Generic[T]):
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
                want_result = tp.get_type_hints(thing)
            except Exception as e:
                want_error = e

            try:
                got_result = tp.get_type_hints(Type.create(thing, cache=type_cache).checkable)
            except Exception as e:
                got_error = e

            if want_result is None and isinstance(want_error, TypeError):
                # Can't get around the fact that checkable is a type
                assert got_result == {}
                assert got_error is None
            else:
                assert got_result == want_result, thing
                assert got_error == want_error, thing

    it "allows attrs helpers", type_cache: strcs.TypeCache:

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
            checkable = Type.create(kls, cache=type_cache).checkable
            is_attrs = attrs.has(kls)
            assert is_attrs == attrs.has(checkable)
            if is_attrs:
                assert attrs.fields(kls) == attrs.fields(checkable)  # type: ignore[arg-type]

    it "allows dataclasses helpers", type_cache: strcs.TypeCache:

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
            checkable = Type.create(kls, cache=type_cache).checkable
            is_dataclass = dataclasses.is_dataclass(kls)
            assert is_dataclass == dataclasses.is_dataclass(checkable)
            if is_dataclass:
                assert dataclasses.fields(kls) == dataclasses.fields(checkable)  # type: ignore[arg-type]
