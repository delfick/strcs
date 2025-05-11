"""
There is a limitation whereby unresolved string type annotations will cause
errors as ``strcs`` won't know what object the string represents. ``strcs`` offers a helper
function based off ``typing.get_type_hints`` for resolving string type
annotations. It will automatically be used on any class that ``strcs`` needs to work with
unless the ``auto_resolve_string_annotations=False`` is given to ``strcs.CreateRegister``.

.. autofunction:: strcs.resolve_types

"""

import dataclasses
import functools
import operator
import sys
import types
import typing
from collections.abc import Callable, Mapping
from typing import (
    TYPE_CHECKING,
    ForwardRef,
    Protocol,
    TypeGuard,
    TypeVar,
    Union,
    cast,
    runtime_checkable,
)

import attrs

if TYPE_CHECKING:
    from .disassemble import TypeCache
    from .register import CreateRegister

T = TypeVar("T")
C = TypeVar("C", bound=type)


class IsField(Protocol):
    type: type
    name: str


@runtime_checkable
class WithResolvedTypes(Protocol[C]):
    """
    Strcs will mark classes it has resolved types for to prevent recursive loops.
    """

    __strcs_types_resolved__: C


class WithCopyWith(Protocol[T]):
    """
    The typing.Generic class has a ``copy_with`` method that lets you create a new
    version of that instance with different arguments.
    """

    __args__: tuple

    def copy_with(self, args: tuple) -> T: ...

    @classmethod
    def has(self, obj: T) -> TypeGuard["WithCopyWith"]:
        return typing.get_origin(obj) is not None and hasattr(obj, "copy_with")


class WithOrigin(Protocol):
    """
    Used to identify objects that have a result from ``typing.get_origin``
    """

    __args__: tuple

    @classmethod
    def has(self, obj: object) -> TypeGuard["WithOrigin"]:
        return typing.get_origin(obj) is not None


class IsUnion(Protocol):
    """
    Used to identify objects that are unions
    """

    __args__: tuple

    @classmethod
    def has(self, obj: object) -> TypeGuard["IsUnion"]:
        return typing.get_origin(obj) in (types.UnionType, Union)


class WithClassGetItem(Protocol[C]):
    """
    Used to find objects that are filled generics.
    """

    __args__: tuple
    __origin__: type[C]

    @classmethod
    def __class_getitem__(self, item: tuple) -> type[C]: ...

    @classmethod
    def has(self, obj: T, origin: type[C]) -> TypeGuard["WithClassGetItem"]:
        return (
            hasattr(typing.get_origin(obj), "__class_getitem__")
            and getattr(obj, "__origin__", None) is origin
            and hasattr(obj, "__args__")
        )


class IsCallable(Protocol):
    """
    Used to identify objects that are unions
    """

    __args__: tuple
    __origin__: WithClassGetItem

    @classmethod
    def has(self, obj: object) -> TypeGuard["IsCallable"]:
        return typing.get_origin(obj) in (Callable,)


def resolve_type(
    typ: object,
    globalns: dict[str, object] | None = None,
    localns: Mapping[str, object] | None = None,
) -> object:
    """
    Resolve a single type annotation such that all ForwardRefs under this type are
    replaced with concrete types.
    """
    origin = typing.get_origin(typ)

    if isinstance(typ, str):
        typ = ForwardRef(typ)

    if isinstance(typ, ForwardRef):
        recursive_guard: frozenset[str] = frozenset()
        return typ._evaluate(globalns, localns, recursive_guard=recursive_guard)

    elif WithCopyWith.has(typ):
        resolved = tuple(resolve_type(t, globalns, localns) for t in typ.__args__)
        if resolved == typ.__args__:
            return typ
        return typ.copy_with(resolved)

    elif IsUnion.has(typ):
        resolved = tuple(resolve_type(t, globalns, localns) for t in typ.__args__)
        if resolved == typ.__args__:
            return typ
        return functools.reduce(operator.or_, resolved)

    elif IsCallable.has(typ):
        resolved = tuple(resolve_type(t, globalns, localns) for t in typ.__args__)
        if len(resolved) == 0:
            return typ
        *args, ret = resolved
        return typ.__origin__.__class_getitem__((args, ret))

    elif isinstance(origin, type) and WithClassGetItem.has(typ, origin):
        resolved = tuple(resolve_type(t, globalns, localns) for t in typ.__args__)
        if resolved == typ.__args__:
            return typ
        return typ.__origin__.__class_getitem__(resolved)

    else:
        return typ


class AnnotationUpdater(Protocol):
    """
    Protocol for an object that can change the annotations on an object
    """

    def __contains__(self, name: object) -> bool: ...

    def update(self, name: str, typ: object) -> None: ...


class FromAnnotations(AnnotationUpdater):
    """
    Changing annotations on a ``__annotations__`` object is easy as that
    is a Mutable mapping.
    """

    def __init__(self, cls: type):
        self.annotations = cls.__annotations__

    def __contains__(self, name: object) -> bool:
        return isinstance(name, str) and name in self.annotations

    def update(self, name: str, typ: object) -> None:
        self.annotations[name] = typ


class FromFields(AnnotationUpdater):
    """
    Updating annotations on an attrs/dataclass requires also updating the fields
    on the class as well
    """

    def __init__(self, cls: type, fields: dict[str, IsField]):
        self.fields = fields
        self.annotations = cls.__annotations__

    def __contains__(self, name: object) -> bool:
        return isinstance(name, str) and name in self.fields

    def update(self, name: str, typ: object) -> None:
        object.__setattr__(self.fields[name], "type", typ)
        self.annotations[name] = typ


def resolve_types(
    cls: C,
    globalns: dict[str, object] | None = None,
    localns: dict[str, object] | None = None,
    *,
    type_cache: Union["CreateRegister", "TypeCache"],
) -> C:
    """
    Resolve any strings and forward annotations in type annotations.

    This is equivalent to ``attrs.resolve_types`` except it doesn't erase Annotations.

    It is automatically used by ``strcs.CreateRegister`` unless the
    ``auto_resolve_string_annotations=False`` option is used when it's created.

    Assumes that the string annotations have been defined when you call this function::

        import attrs
        # or ``dataclasses`` equivalent
        import strcs


        @attrs.define
        class One:
            two: "Two"


        @attrs.define
        class Two:
            ...


        strcs.resolve_types(One)

    Note that if ``from __future__ import annotations`` is used then all types are
    strings and require resolution. In that case if auto resolution on the register
    is turned off then ``strcs.resolve_types`` may be used as a decorator in any
    situation where types are already available at definition:

    .. code-block:: python

        from __future__ import annotations
        import attrs
        import strcs


        @strcs.resolve_types
        class Stuff:
            one: int


        @attrs.define
        class Thing:
            stuff: "Stuff"
            other: "Other"


        @strcs.resolve_types
        @attrs.define
        class Other:
            thing: Thing | None


        strcs.resolve_types(Thing)

    .. note:: Calling resolve_types will modify the fields on the class in place.
    """
    from .register import CreateRegister

    if isinstance(type_cache, CreateRegister):
        type_cache = type_cache.type_cache

    # Calling get_type_hints can be expensive so cache it like how attrs.resolve_types does
    if getattr(cls, "__strcs_types_resolved__", None) != cls:
        allfields: AnnotationUpdater

        if attrs.has(cls):
            allfields = FromFields(cls, {field.name: field for field in attrs.fields(cls)})  # type: ignore[misc]

        elif dataclasses.is_dataclass(cls):
            allfields = FromFields(cls, {field.name: field for field in dataclasses.fields(cls)})  # type: ignore[misc]

        elif isinstance(cls, type) and hasattr(cls, "__annotations__"):
            allfields = FromAnnotations(cls)

        else:
            return cls

        cast(WithResolvedTypes[C], cls).__strcs_types_resolved__ = cls

        # Copied from standard library typing.get_type_hints
        # Cause I need globals/locals to resolve nested types that don't have forwardrefs

        for base in reversed(cls.__mro__):
            if globalns is None:
                base_globals = getattr(sys.modules.get(base.__module__, None), "__dict__", {})
            else:
                base_globals = globalns
            ann = base.__dict__.get("__annotations__", {})
            if isinstance(ann, types.GetSetDescriptorType):
                ann = {}
            base_locals = dict(vars(base)) if localns is None else localns
            if localns is None and globalns is None:
                # This is surprising, but required.  Before Python 3.10,
                # get_type_hints only evaluated the globalns of
                # a class.  To maintain backwards compatibility, we reverse
                # the globalns and localns order so that eval() looks into
                # *base_globals* first rather than *base_locals*.
                # This only affects ForwardRefs.
                base_globals, base_locals = base_locals, base_globals

            for name, value in ann.items():
                if value is None:
                    value = type(None)
                if isinstance(value, str):
                    value = ForwardRef(value, is_argument=False, is_class=True)

                if name in allfields:
                    disassembled = type_cache.disassemble(value)

                    resolved = resolve_type(disassembled.extracted, base_globals, base_locals)
                    if value != resolved and value in type_cache:
                        del type_cache[value]

                    if isinstance(resolved, type):
                        resolve_types(resolved, base_globals, base_locals, type_cache=type_cache)

                    allfields.update(name, disassembled.reassemble(resolved))

    type_cache.clear()
    return cls
