import abc
import fnmatch
import functools
import inspect
import operator
import types
import typing as tp
from collections.abc import Mapping

import cattrs
from attrs import define

from . import errors

T = tp.TypeVar("T")
U = tp.TypeVar("U")


class Empty:
    pass


class NarrowCB(tp.Protocol):
    def __call__(self, *patterns: str, obj: Mapping | object = Empty) -> dict[str, object]:
        ...


class Narrower:
    """
    Used to take some dictionary and return a constrained version of it

    Usage::

        narrower = Narrower(obj)
        narrowed = narrower.narrow("key1", "key2")

    Where the narrow options are fnmatch globs for top level keys in the obj
    and the obj is either a Mapping (dictionary like) or any other kind of object.

    If a pattern has a dot in it, then it will be used to match against nested objects
    with preference given to keys that match with the dot.

    So::

        obj = {"a": {"b": {"d": 4, "e": 5}}, "a.b": 1, "a.c": 3}
        assert Narrower(obj).narrow("a.b") == {"a.b": 1}
        assert Narrower(obj).narrow("a.c") == {"a.c": 3}
        assert Narrower(obj).narrow("a.b.d") == {"a.b.d": 4}
        assert Narrower(obj).narrow("a.b.*") == {"a.b.d": 4, "a.b.e": 5}
        assert Narrower(obj).narrow("a.b*") == {"a.b.d": 4, "a.b.e": 5}

        obj = {"a": {"b": {"d": 4, "e": 5}}, "a.b": {"f": 6}, "a.bc": True}
        assert Narrower(obj).narrow("a.b") == {"a.b": {"f": 6}}
        assert Narrower(obj).narrow("a.b.d") == {"a.b.d": 4}
        assert Narrower(obj).narrow("a.b.*") == {"a.b.d": 4, "a.b.e": 5, "a.b.f": 6}
        assert Narrower(obj).narrow("a.b*") == {"a.b": {"f": 6}, "a.bc": True}
    """

    @define
    class Further:
        value: object
        patterns: list[str]

    class Progress:
        def __init__(self, obj: Mapping | object):
            self.obj = obj

            self.further: dict[str, Narrower.Further] = {}
            self.collected: dict[str, object] = {}
            self.obj_is_mapping = isinstance(self.obj, Mapping)

        def collect(self, narrow: NarrowCB) -> dict[str, object]:
            for n, ft in self.further.items():
                found = narrow(*ft.patterns, obj=ft.value)
                for k, v in found.items():
                    key = f"{n}.{k}"
                    if key not in self.collected:
                        self.collected[key] = v

            return self.collected

        def add(self, pattern: str, n: str, v: object):
            if n in self.collected:
                return

            patt = pattern
            if pattern.startswith("*"):
                patt = f"{n}{pattern[1:]}"

            is_nestable = not (
                not isinstance(v, (Mapping, type))
                and v.__class__.__module__ in ("__builtin__", "builtins")
            )

            if patt.startswith(f"{n}.") and is_nestable:
                if n not in self.further:
                    self.further[n] = Narrower.Further(value=v, patterns=[])
                self.further[n].patterns.append(patt[len(f"{n}.") :])
            elif fnmatch.fnmatch(n, patt):
                self.collected[n] = v

    def __init__(self, obj: Mapping | object):
        self.obj = obj

    def keys_from(self, options: object) -> tp.Iterable[str]:
        if isinstance(options, (Mapping, tp.Iterable)):
            yield from iter(options)
        else:
            yield from [n for n in dir(options) if not n.startswith("_")]

    def narrow(self, *patterns: str, obj: Mapping | object = Empty) -> dict[str, object]:
        if not patterns:
            return {}

        if obj is Empty:
            obj = self.obj
        progress = self.Progress(obj)

        for pattern in patterns:
            if pattern.startswith("."):
                pattern = pattern[1:]
            for n in self.keys_from(obj):
                if progress.obj_is_mapping:
                    v = tp.cast(Mapping, obj)[n]
                else:
                    v = getattr(obj, n)

                progress.add(pattern, n, v)

        return progress.collect(self.narrow)


class IsAnnotated(tp.Protocol):
    __args__: tuple

    def copy_with(self, args: tuple) -> type:
        ...

    @classmethod
    def has(self, typ: object) -> tp.TypeGuard["IsAnnotated"]:
        return tp.get_origin(typ) is tp.Annotated and hasattr(typ, "__args__")


def extract_type(typ: object) -> tuple[bool, object, type]:
    """
    Given some type, return a tuple of (optional, type_or_annotated, type)

    So str would return (False, str, str)

    list[str] would return (False, list[str], list)

    whereas tp.Optional[str] would return (True, str, str)

    and str | bool would return (False, str | bool, str | bool)

    but tp.Optional[str | bool] would return (True, str | bool, str | bool)

    And tp.Annotated[list, "things"] would return (False, tp.Annotated[list, "things"], list)

    but tp.Annotated[list | None, "things"] would return (True, tp.Annotated[list, "things"], list)
    """
    original = typ
    annotated: IsAnnotated | None = None

    if IsAnnotated.has(typ):
        annotated = typ
        typ = typ.__args__[0]

    def origin_or_type(typ: object) -> object:
        orig = tp.get_origin(typ)
        if not isinstance(orig, type) or orig in (None, types.UnionType, tp.Union):
            return typ
        else:
            return orig

    optional = False
    extracted = typ
    if tp.get_origin(typ) in (types.UnionType, tp.Union):
        if type(None) in tp.get_args(typ):
            optional = True

            remaining = tuple(a for a in tp.get_args(typ) if a not in (types.NoneType,))
            if len(remaining) == 1:
                extracted = remaining[0]
                typ = origin_or_type(extracted)
            else:
                typ = functools.reduce(operator.or_, remaining)
                extracted = typ
    else:
        typ = origin_or_type(typ)

    class InstanceCheckMeta(type):
        def __repr__(self) -> str:
            return repr(typ)

        def __instancecheck__(self, obj: object) -> bool:
            return isinstance(obj, tp.cast(type, typ))

        def __eq__(self, o: object) -> bool:
            return o == typ

        def __hash__(self) -> int:
            return hash(typ)

    ret: object = extracted
    if annotated is not None:
        ret = annotated.copy_with((extracted,))

    class CombinedMeta(InstanceCheckMeta, abc.ABCMeta):
        pass

    class InstanceCheck(abc.ABC, metaclass=CombinedMeta):
        _typ = typ
        _original = original
        _optional = optional
        _returning = ret

        def __new__(mcls, *args, **kwargs):
            return typ(*args, **kwargs)

        @classmethod
        def __subclasshook__(cls, C: type) -> bool:
            if not isinstance(typ, type):
                return False

            if hasattr(C, "_typ") and isinstance(C, abc.ABCMeta):
                C = tp.cast(type[InstanceCheck], C)
                if isinstance(C._typ, type):
                    C = C._typ
            return issubclass(C, typ)

    if hasattr(typ, "__args__"):
        InstanceCheck.__args__ = typ.__args__  # type: ignore
    if hasattr(typ, "__origin__"):
        InstanceCheck.__origin__ = typ.__origin__  # type: ignore
    if hasattr(typ, "__attrs_attrs__"):
        InstanceCheck.__attrs_attrs__ = typ.__attrs_attrs__  # type:ignore
    if hasattr(typ, "__dataclass_fields__"):
        InstanceCheck.__dataclass_fields__ = typ.__dataclass_fields__  # type:ignore

    return optional, ret, InstanceCheck


class Meta:
    """
    A store for holding data and cattrs converter

    Data may be added and removed using dictionary syntax (__setitem__, __delitem__, __contains__, update)

    Data may not be retrieved using dictionary syntax, but rather from one of these methods:

    .. automethod:: find_by_type

    .. automethod:: retrieve_one

    .. automethod:: retrieve_patterns

    Because getting data depends on the type of the data as well as the name of the data in the store
    """

    def __init__(
        self,
        data: dict[str, object] | None = None,
        converter: cattrs.Converter | None = None,
    ):
        self.converter = converter or cattrs.GenConverter()
        self.data = data if data is not None else {}

    def clone(
        self,
        data_extra: tp.Mapping[str, object] | None = None,
        data_override: tp.Mapping[str, object] | None = None,
        converter: cattrs.Converter | None = None,
    ) -> "Meta":
        if converter is None:
            converter = self.converter

        if data_override is None:
            data = dict(self.data)
        else:
            data = dict(data_override)

        if data_extra:
            data.update(data_extra)

        return Meta(data, converter)

    def __setitem__(self, name: str, value: object) -> None:
        self.data[name] = value

    def __delitem__(self, name: str) -> None:
        del self.data[name]

    def __contains__(self, name: str) -> bool:
        return name in self.data

    def update(self, data: dict[str, object]) -> None:
        self.data.update(data)

    def find_by_type(
        self, typ: object, data: tp.Mapping[str, object] | type[Empty] = Empty
    ) -> tuple[bool, dict[str, object]]:
        """
        Return (optional, found)

        Where optional is True if the type is a tp.Optional and found is a dictionary
        of names in Meta to the found data for that name, which matches the specified type
        """
        if data is Empty:
            data = self.data

        data = tp.cast(dict[str, object], data)

        if typ is object:
            return False, data

        optional, _, typ = extract_type(typ)
        available: dict[str, object] = {n: v for n, v in data.items() if isinstance(v, typ)}

        remove_bools = typ == int
        ags = getattr(typ, "__args__", None)
        if ags:
            if int in ags and bool not in ags:
                remove_bools = True

        if remove_bools:
            available = {n: v for n, v in available.items() if not isinstance(v, bool)}

        return optional, available

    def retrieve_patterns(self, typ: object, *patterns: str) -> dict[str, object]:
        """
        Retrieve a dictionary of key to value for this patterns restrictions.
        """
        data = self.data
        if patterns:
            data = Narrower(data).narrow(*patterns)

        _, found = self.find_by_type(typ, data=data)
        return found

    @tp.overload
    def retrieve_one(
        self,
        typ: type[T],
        *patterns: str,
        default: object = inspect._empty,
        refined_type: None = None,
    ) -> T:
        ...

    @tp.overload
    def retrieve_one(
        self, typ: object, *patterns: str, default: object = inspect._empty, refined_type: T
    ) -> T:
        ...

    def retrieve_one(
        self,
        typ: type[T] | object,
        *patterns: str,
        default: object = inspect._empty,
        refined_type: T | None = None,
    ) -> object:
        """
        Retrieve a single value for this type and patterns restrictions

        If we get a single value from the type restriction alone we ignore the patterns restrictions

        Multiple patterns can be used to cater for a situation where we know a meta may contain only
        one of a few possibilities and we want to retrieve whichever is in use for that meta

        Raise an error if we can't find exactly one value
        """
        data = self.data
        if patterns:
            with_patterns = Narrower(data).narrow(*patterns)
            if with_patterns or typ is object:
                data = with_patterns
            elif default is not inspect._empty:
                return tp.cast(T, default)

        optional, found = self.find_by_type(typ, data=data)

        if patterns and data and not found and not optional:
            raise errors.FoundWithWrongType(patterns=list(patterns), want=typ)

        if optional and not found:
            return tp.cast(T, None)

        if len(found) == 1:
            for thing in found.values():
                return thing

        if found:
            raise errors.MultipleNamesForType(want=typ, found=sorted(found))

        if default is not inspect._empty:
            return tp.cast(T, default)

        raise errors.NoDataByTypeName(
            want=typ,
            patterns=sorted(patterns),
            available={n: type(v) for n, v in self.data.items()},
        )
