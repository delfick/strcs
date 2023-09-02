import functools
import operator
import sys
import types
import typing as tp
from dataclasses import fields as dataclass_fields
from dataclasses import is_dataclass

from attrs import fields as attrs_fields
from attrs import has as is_attrs

if tp.TYPE_CHECKING:
    from ..register import CreateRegister
    from .base import TypeCache

T = tp.TypeVar("T")
C = tp.TypeVar("C", bound=type)


class IsField(tp.Protocol):
    type: type
    name: str


@tp.runtime_checkable
class WithResolvedTypes(tp.Protocol[C]):
    __strcs_types_resolved__: C


class WithCopyWith(tp.Protocol[T]):
    __args__: tuple

    def copy_with(self, args: tuple) -> T:
        ...

    @classmethod
    def has(self, obj: T) -> tp.TypeGuard["WithCopyWith"]:
        return tp.get_origin(obj) is not None and hasattr(obj, "copy_with")


class WithOrigin(tp.Protocol):
    __args__: tuple

    @classmethod
    def has(self, obj: object) -> tp.TypeGuard["WithOrigin"]:
        return tp.get_origin(obj) is not None


class IsUnion(tp.Protocol):
    __args__: tuple

    @classmethod
    def has(self, obj: object) -> tp.TypeGuard["IsUnion"]:
        return tp.get_origin(obj) in (types.UnionType, tp.Union)


class WithClassGetItem(tp.Protocol[C]):
    __args__: tuple
    __origin__: type[C]

    @classmethod
    def __class_getitem__(self, item: tuple) -> type[C]:
        ...

    @classmethod
    def has(self, obj: T, origin: type[C]) -> tp.TypeGuard["WithClassGetItem"]:
        return (
            hasattr(tp.get_origin(obj), "__class_getitem__")
            and getattr(obj, "__origin__", None) is origin
            and hasattr(obj, "__args__")
        )


def resolve_type(
    typ: object,
    globalns: dict[str, object] | None = None,
    localns: dict[str, object] | None = None,
) -> object:
    origin = tp.get_origin(typ)

    if isinstance(typ, str):
        typ = tp.ForwardRef(typ)

    if isinstance(typ, tp.ForwardRef):
        return typ._evaluate(globalns, localns, set())  # type: ignore

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

    elif isinstance(origin, type) and WithClassGetItem.has(typ, origin):
        resolved = tuple(resolve_type(t, globalns, localns) for t in typ.__args__)
        if resolved == typ.__args__:
            return typ
        return typ.__origin__.__class_getitem__(
            tuple(resolve_type(t, globalns, localns) for t in typ.__args__)
        )

    else:
        return typ


class AnnotationUpdater(tp.Protocol):
    def __contains__(self, name: object) -> bool:
        ...

    def update(self, name: str, typ: object) -> None:
        ...


class FromAnnotations(AnnotationUpdater):
    def __init__(self, cls: type):
        self.annotations = cls.__annotations__

    def __contains__(self, name: object) -> bool:
        return isinstance(name, str) and name in self.annotations

    def update(self, name: str, typ: object) -> None:
        self.annotations[name] = typ


class FromFields(AnnotationUpdater):
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
    type_cache: tp.Union["CreateRegister", "TypeCache"]
) -> C:
    """
    Resolve any strings and forward annotations in type annotations.

    Assumes that the string annotations have been defined when you call this function::

        from attrs import define
        # or ``from dataclasses import dataclass as define``
        import strcs


        @define
        class One:
            two: "Two"


        @define
        class Two:
            ...


        strcs.resolve_types(One)

    This is equivalent to ``attrs.resolve_types`` except it doesn't erase Annotations.
    """
    from ..register import CreateRegister

    if isinstance(type_cache, CreateRegister):
        type_cache = type_cache.type_cache

    # Calling get_type_hints can be expensive so cache it like how attrs.resolve_types does
    if getattr(cls, "__strcs_types_resolved__", None) != cls:
        allfields: AnnotationUpdater

        if is_attrs(cls):
            allfields = FromFields(cls, {field.name: field for field in attrs_fields(cls)})

        elif is_dataclass(cls):
            allfields = FromFields(cls, {field.name: field for field in dataclass_fields(cls)})

        elif isinstance(cls, type) and hasattr(cls, "__annotations__"):
            allfields = FromAnnotations(cls)

        else:
            return cls

        tp.cast(WithResolvedTypes[C], cls).__strcs_types_resolved__ = cls

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
                    value = tp.ForwardRef(value, is_argument=False, is_class=True)

                if name in allfields:
                    from .base import Type

                    disassembled = Type.create(value, cache=type_cache, expect=object)

                    resolved = resolve_type(disassembled.extracted, base_globals, base_locals)
                    if value != resolved and value in type_cache:
                        del type_cache[value]

                    if isinstance(resolved, type):
                        resolve_types(resolved, base_globals, base_locals, type_cache=type_cache)

                    allfields.update(name, disassembled.reassemble(resolved))

    type_cache.clear()
    return cls