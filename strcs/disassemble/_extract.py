import functools
import operator
import types
import typing
from collections.abc import Sequence
from typing import Annotated, Protocol, TypeGuard, TypeVar

from ..standard import union_types

T = TypeVar("T")


class IsAnnotated(Protocol):
    """
    Protocol class used to determine if an object is a typing.Annotated

    Usage is:

    .. code-block:: python

        from typing import Annotated

        typ = Annotated[int, "one"]

        assert IsAnnotated.has(typ)

    These kind of objects have three properties we care about specifically:

    ``__args__``
        Will be a one item tuple with the first value the type was instantiated with

    ``__metadata__``
        Will be a tuple of all other items passed into the annotated typ variable

    ``copy_with(tuple) -> type``
        Returns a new annotated type variable with the first value of the passed
        in tuple as the type, with the existing metadata.
    """

    __args__: tuple
    __metadata__: tuple

    def copy_with(self, args: tuple) -> type: ...

    @classmethod
    def has(self, typ: object) -> TypeGuard["IsAnnotated"]:
        return (
            typing.get_origin(typ) is Annotated
            and hasattr(typ, "__args__")
            and hasattr(typ, "__metadata__")
        )


def extract_optional(typ: T) -> tuple[bool, T]:
    """
    Given a type annotation, return a boolean indicating whether the type is optional,
    and a new type without the optional:

    .. code-block:: python

        from strcs.disassemble import extract_optional
        from typing import Optional, Annotated

        assert extract_optional(Optional[int]) == (True, int)
        assert extract_optional(int | None) == (True, int)
        assert extract_optional(int | str | None) == (True, int | str)

        assert extract_optional(int) == (False, int)
        assert extract_optional(int | str) == (False, int | str)

        assert extract_optional(Annotated[int | str | None, "one"]) == (False, Annotated[int | str | None, "one"])
    """
    optional = False
    if typing.get_origin(typ) in union_types:
        if type(None) in typing.get_args(typ):
            optional = True

            remaining = tuple(a for a in typing.get_args(typ) if a not in (types.NoneType,))
            if len(remaining) == 1:
                typ = remaining[0]
            else:
                typ = functools.reduce(operator.or_, remaining)

    return optional, typ


def extract_annotation(typ: T) -> tuple[T, IsAnnotated | None, Sequence[object] | None]:
    """
    Given a type annotation return it without any annotation with the annotation it had:

    .. code-block:: python

        from strcs.disassemble import extract_annotation

        assert extract_annotation(int) == (int, None, None)
        assert extract_annotation(int | None) == (int | None, None, None)

        with_annotation = Annotated[int, "one", "two"]
        assert extract_annotation(with_annotation) == (int, with_annotation, ("one", "two"))
    """
    if IsAnnotated.has(typ):
        return typ.__args__[0], typ, typ.__metadata__
    else:
        return typ, None, None
