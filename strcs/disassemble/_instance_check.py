import abc
import typing as tp

from ..standard import union_types

if tp.TYPE_CHECKING:
    from ._base import Type


class InstanceCheckMeta(abc.ABCMeta):
    """The base type for the metclass given to the Checkable class"""

    pass


class InstanceCheck(abc.ABC):
    """
    Returned from the ``checkable`` property on a :class:`strcs.Type`. This object can be used wherever
    you'd otherwise want to treat the :class:`strcs.Type` object as a python ``type`` regardless of whether
    it's in a union, or annotated, or a generic or some other non-type python object.

    It will be different depending on whether the type is for a union or not.

    In either cases, the checkable will also have a ``Meta`` object on it containing information.

    The behaviour of the checkable is based around the information on ``Meta``

    For both
    --------

    The following methods called with the ``checkable`` object will be equivalent to calling the function
    with the ``extracted`` object from :class:`strcs.Type`

    * ``typing.get_origin``
    * ``typing.get_args``
    * ``typing.get_type_hints`` unless calling this with the ``extracted`` raises a ``TypeError``. In those
      cases, an empty dictionary will be returned instead.
    * ``attrs.fields``
    * ``attrs.has``
    * ``dataclasses.fields``
    * ``dataclasses.isdataclass``
    * ``type``
    * ``hash``

    For objects that aren't unions or an optional type
    --------------------------------------------------

    For these, the ``check_against`` will be the return of ``disassembled.origin``

    * If ``typing.get_origin(extracted)`` is a type, then that
    * otherwise if ``extracted`` is a type, then that
    * otherwise ``type(extracted)``

    The following behaviour is implemented:

    * ``repr(checkable)`` == ``repr(check_against)``
    * ``isinstance(obj, checkable)`` will return true if the object is None and we are optional, otherwise it will
      is equivalent to ``isinstance(obj, check_against)``
    * ``obj == checkable`` == ``obj == check_against``
    * ``checkable(...)`` is equivalent to ``extracted(...)``
    * ``issubclass(obj, checkable)`` is equivalent to ``issubclass(obj, check_against)`` and works with other checkable instances

    For Unions
    ----------

    For these, the ``check_against`` will a tuple of checkable instances for each of the items in the union. Note
    that a union that is one item with ``None`` is considered an optional of that one item rather than a union.

    The following behaviour is implemented:

    * ``repr(checkable)`` will return a pipe separated string of all the checkable instances for each
      non-none item in the union
    * ``isinstance(obj, checkable)`` will return true if the object is equivalent for any of the types
      in the union
    * ``obj == checkable`` == ``any(obj == ch for ch in check_against)``
    * ``checkable(...)`` will raise an error
    * ``issubclass(obj, checkable)`` is equivalent to ``issubclass(obj, check_against)`` and works with other checkable instances

    Properties
    ----------
    """

    class Meta:
        typ: object
        "Either the extracted type from the original or it's ``typing.get_origin`` value if that's not a type"

        original: object
        "The original object wrapped by the :class:`strcs.Type`"

        extracted: object
        "The extracted object from the :class:`strcs.Type`"

        optional: bool
        "True if the value being wrapped is a ``typing.Optional`` or Union with ``None``"

        union_types: tuple["Type", ...] | None
        "A tuple of the types in the union if it's a union, otherwise ``None``"

        disassembled: "Type"
        "The original :class:`strcs.Type` object"

        without_optional: object
        "The original object given to :class:`strcs.Type` without a wrapping ``Optional``"

        without_annotation: object
        "The original object given to :class:`strcs.Type` without a wrapping ``typing.Annotation``"


def create_checkable(disassembled: "Type") -> type[InstanceCheck]:
    class Meta(InstanceCheck.Meta):
        original = disassembled.original
        extracted = disassembled.without_annotation
        optional = disassembled.optional
        without_optional = disassembled.without_optional
        without_annotation = disassembled.without_annotation

    Meta.disassembled = disassembled
    check_against: object | None

    if tp.get_origin(Meta.extracted) in union_types:
        check_against = tuple(disassembled.disassemble(a) for a in tp.get_args(Meta.extracted))

        reprstr = " | ".join(repr(c) for c in check_against)

        Meta.typ = Meta.extracted
        Meta.union_types = check_against
    else:
        check_against = (
            disassembled.type_alias
            if disassembled.is_type_alias
            else None
            if Meta.extracted is None
            else disassembled.origin_type
        )

        reprstr = repr(check_against)

        Meta.typ = disassembled.origin
        Meta.union_types = None

    Checker = _create_checker(disassembled, check_against, Meta, reprstr)

    typ = disassembled.origin
    extracted = Meta.extracted

    if hasattr(extracted, "__args__"):
        Checker.__args__ = extracted.__args__  # type: ignore
    if hasattr(extracted, "__origin__"):
        Checker.__origin__ = extracted.__origin__  # type: ignore
    if hasattr(extracted, "__supertype__"):
        Checker.__supertype__ = extracted.__supertype__  # type: ignore
    if hasattr(extracted, "__parameters__"):
        Checker.__parameters__ = extracted.__parameters__  # type: ignore
    if hasattr(extracted, "__annotations__"):
        Checker.__annotations__ = extracted.__annotations__  # type: ignore
    if hasattr(typ, "__attrs_attrs__"):
        Checker.__attrs_attrs__ = typ.__attrs_attrs__  # type:ignore
    if hasattr(typ, "__dataclass_fields__"):
        Checker.__dataclass_fields__ = typ.__dataclass_fields__  # type:ignore

    return Checker


def _create_checker(
    disassembled: "Type",
    check_against: object,
    M: type[InstanceCheck.Meta],
    reprstr: str,
) -> type[InstanceCheck]:
    comparer = disassembled.cache.comparer

    class CheckerMeta(InstanceCheckMeta):
        def __repr__(self) -> str:
            return reprstr

        def __instancecheck__(self, obj: object) -> bool:
            return comparer.isinstance(obj, M.original)

        def __eq__(self, o: object) -> bool:
            return o == disassembled or o is type(M.extracted)

        def __hash__(self) -> int:
            if type(M.extracted) is type:
                return hash(M.extracted)
            else:
                return id(self)

        @property  # type:ignore
        def __class__(self) -> type:
            return type(M.extracted)

        @classmethod
        def __subclasscheck__(cls, C: type) -> bool:
            if C == CombinedMeta:
                return True

            return comparer.issubclass(C, M.original)

    class CombinedMeta(CheckerMeta, abc.ABCMeta):
        pass

    class Checker(InstanceCheck, metaclass=CombinedMeta):
        def __new__(mcls, *args, **kwargs):
            if callable(check_against):
                return check_against(*args, **kwargs)
            raise ValueError(f"Cannot instantiate this type: {check_against}")

        Meta = M

    return Checker
