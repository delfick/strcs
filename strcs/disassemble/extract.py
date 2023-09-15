import functools
import operator
import types
import typing as tp

from ..standard import union_types

T = tp.TypeVar("T")


class IsAnnotated(tp.Protocol):
    __args__: tuple
    __metadata__: tuple

    def copy_with(self, args: tuple) -> type:
        ...

    @classmethod
    def has(self, typ: object) -> tp.TypeGuard["IsAnnotated"]:
        return (
            tp.get_origin(typ) is tp.Annotated
            and hasattr(typ, "__args__")
            and hasattr(typ, "__metadata__")
        )


def extract_optional(typ: T) -> tuple[bool, T]:
    optional = False
    if tp.get_origin(typ) in union_types:
        if type(None) in tp.get_args(typ):
            optional = True

            remaining = tuple(a for a in tp.get_args(typ) if a not in (types.NoneType,))
            if len(remaining) == 1:
                typ = remaining[0]
            else:
                typ = functools.reduce(operator.or_, remaining)

    return optional, typ


def extract_annotation(typ: T) -> tuple[T, IsAnnotated | None, object | None]:
    if IsAnnotated.has(typ):
        return typ.__args__[0], typ, typ.__metadata__[0]
    else:
        return typ, None, None
