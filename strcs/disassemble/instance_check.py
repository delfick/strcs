import abc
import typing as tp

from ..standard import union_types

if tp.TYPE_CHECKING:
    from .base import Type


class InstanceCheckMeta(type):
    """The base type for the metclass given to the Checkable class"""

    pass


class InstanceCheck(abc.ABC):
    """
    Returned from the ``checkable`` property on a ``strcs.Type``. This object can be used wherever
    you'd otherwise want to treat the ``strcs.Type`` object as a python ``type`` regardless of whether
    it's in a union, or annotated, or a generic or some other non-type python object.

    It will be different depending on whether the type is for a union or not.

    In either cases, the checkable will also have a ``Meta`` object on it containing information.

    The behaviour of the checkable is based around the information on ``Meta``

    For both
    --------

    The following methods called with the ``checkable`` object will be equivalent to calling the function
    with the ``extracted`` object from ``strcs.Type``

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

    The ``checkable.matches`` method will check that another type is equivalent depending on the options provided.

    * ``subclass=True``: If a subclass can be counted as matching
    * ``allow_missing_typevars``: If an unfilled generic counts as matching a filled generic
    * For unions, it ill match another union if there is a complete overlap in items between both unions

    For classes or unions that are only one type with None
    ------------------------------------------------------

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
        "The original object wrapped by the ``strcs.Type``"

        extracted: object
        "The extracted object from the ``strcs.Type``"

        optional: bool
        "True if the value being wrapped is a ``typing.Optional`` or Union with ``None``"

        union_types: tuple[type["InstanceCheck"]] | None
        "A tuple of the types in the union if it's a union, otherwise ``None``"

        disassembled: "Type"
        "The original ``strcs.Type`` object"

        without_optional: object
        "The original object given to ``strcs.Type`` without a wrapping ``Optional``"

        without_annotation: object
        "The original object given to ``strcs.Type`` without a wrapping ``typing.Annotation``"

    @classmethod
    def matches(
        cls,
        other: type["InstanceCheck"],
        subclasses: bool = False,
        allow_missing_typevars: bool = True,
    ) -> bool:
        """
        Used to determine if this is equivalent to another object.
        """
        raise NotImplementedError()


def create_checkable(disassembled: "Type") -> type[InstanceCheck]:
    class Meta(InstanceCheck.Meta):
        original = disassembled.original
        extracted = disassembled.extracted
        optional = disassembled.optional
        without_optional = disassembled.without_optional
        without_annotation = disassembled.without_annotation

    Meta.disassembled = disassembled

    if tp.get_origin(Meta.extracted) in union_types:
        check_against = tuple(
            disassembled.disassemble(object, a).checkable for a in tp.get_args(Meta.extracted)
        )

        Meta.typ = Meta.extracted
        Meta.union_types = tp.cast(tuple[type[InstanceCheck]], check_against)
        Checker = _checker_union(disassembled, check_against, Meta)
    else:
        check_against_single: type | None = disassembled.origin
        if Meta.extracted is None:
            check_against_single = None

        Meta.typ = disassembled.origin
        Meta.union_types = None
        Checker = _checker_single(disassembled, check_against_single, Meta)

    if hasattr(Meta.extracted, "__args__"):
        Checker.__args__ = Meta.extracted.__args__  # type: ignore
    if hasattr(Meta.extracted, "__origin__"):
        Checker.__origin__ = Meta.extracted.__origin__  # type: ignore
    if hasattr(Meta.extracted, "__annotations__"):
        Checker.__annotations__ = Meta.extracted.__annotations__  # type: ignore
    if hasattr(Checker.Meta.typ, "__attrs_attrs__"):
        Checker.__attrs_attrs__ = Checker.Meta.typ.__attrs_attrs__  # type:ignore
    if hasattr(Checker.Meta.typ, "__dataclass_fields__"):
        Checker.__dataclass_fields__ = Checker.Meta.typ.__dataclass_fields__  # type:ignore

    return Checker


def _checker_union(
    disassembled: "Type",
    check_against: tp.Sequence[type],
    M: type[InstanceCheck.Meta],
) -> type[InstanceCheck]:

    reprstr = " | ".join(repr(c) for c in check_against)

    class CheckerMeta(InstanceCheckMeta):
        def __repr__(self) -> str:
            return reprstr

        def __instancecheck__(self, obj: object) -> bool:
            return (obj is None and disassembled.optional) or isinstance(obj, tuple(check_against))

        def __eq__(self, o: object) -> bool:
            return any(o == ch for ch in check_against)

        def __hash__(self) -> int:
            return hash(M.extracted)

        @property  # type:ignore
        def __class__(self) -> type:
            return type(M.extracted)

    class CombinedMeta(CheckerMeta, abc.ABCMeta):
        pass

    class Checker(InstanceCheck, metaclass=CombinedMeta):
        def __new__(mcls, *args, **kwargs):
            raise ValueError(f"Cannot instantiate a union type: {check_against}")

        @classmethod
        def __subclasshook__(cls, C: type) -> bool:
            if C == CombinedMeta:
                return True

            if hasattr(C, "Meta") and issubclass(C.Meta, InstanceCheck.Meta):
                if isinstance(C.Meta.typ, type):
                    C = C.Meta.typ
            return issubclass(C, tuple(check_against))

        @classmethod
        def matches(
            cls,
            other: type[InstanceCheck],
            subclasses: bool = False,
            allow_missing_typevars=False,
        ) -> bool:
            if cls.Meta.union_types is None or other.Meta.union_types is None:
                return False

            if subclasses:
                # I want it so that everything in cls is a subclass of other
                if not all(issubclass(typ, other) for typ in cls.Meta.union_types):
                    return False

                # And for all types in other to have a matching subclass in cls
                if not all(
                    any(issubclass(cls_typ, other_typ) for cls_typ in cls.Meta.union_types)
                    for other_typ in other.Meta.union_types
                ):
                    return False

                return True
            else:
                for typ in cls.Meta.union_types:
                    found = False
                    for other_typ in other.Meta.union_types:
                        if typ.matches(other_typ):
                            found = True
                            break
                    if not found:
                        return False

                if len(cls.Meta.union_types) == len(other.Meta.union_types):
                    return True

                for typ in other.Meta.union_types:
                    found = False
                    for cls_typ in cls.Meta.union_types:
                        if other_typ.matches(cls_typ):
                            found = True
                            break
                    if not found:
                        return False

                return True

        Meta = M

    return Checker


def _checker_single(
    disassembled: "Type",
    check_against: object | None,
    M: type[InstanceCheck.Meta],
) -> type[InstanceCheck]:
    from .base import Type

    class CheckerMeta(InstanceCheckMeta):
        def __repr__(self) -> str:
            return repr(check_against)

        def __instancecheck__(self, obj: object) -> bool:
            if check_against is None:
                return obj is None

            return (obj is None and disassembled.optional) or isinstance(
                obj, tp.cast(type, check_against)
            )

        def __eq__(self, o: object) -> bool:
            return o == check_against

        def __hash__(self) -> int:
            return hash(M.extracted)

        @property  # type:ignore
        def __class__(self) -> type:
            return type(M.extracted)

    class CombinedMeta(CheckerMeta, abc.ABCMeta):
        pass

    class Checker(InstanceCheck, metaclass=CombinedMeta):
        def __new__(mcls, *args, **kwargs):
            return check_against(*args, **kwargs)

        @classmethod
        def __subclasshook__(cls, C: type) -> bool:
            if C == CombinedMeta:
                return True

            if not isinstance(check_against, type):
                return False

            if hasattr(C, "Meta") and issubclass(C.Meta, InstanceCheck.Meta):
                if isinstance(C.Meta.typ, type):
                    C = C.Meta.typ

            if not issubclass(C, check_against):
                return False

            want = disassembled.disassemble(object, C)
            for w, g in zip(want.mro.all_vars, disassembled.mro.all_vars):
                if isinstance(w, Type) and isinstance(g, Type):
                    if not issubclass(w.checkable, g.checkable):
                        return False

            return True

        @classmethod
        def matches(
            cls,
            other: type[InstanceCheck],
            subclasses: bool = False,
            allow_missing_typevars=False,
        ) -> bool:
            if subclasses:
                if not issubclass(cls, other):
                    return False

                for ctv, otv in zip(
                    cls.Meta.disassembled.mro.all_vars,
                    other.Meta.disassembled.mro.all_vars,
                ):
                    if isinstance(ctv, Type) and isinstance(otv, Type):
                        if not ctv.checkable.matches(otv.checkable, subclasses=True):
                            return False
                    elif otv is Type.Missing and not allow_missing_typevars:
                        return False

                return True
            else:
                return (
                    cls.Meta.typ == other.Meta.typ
                    and cls.Meta.disassembled.mro.all_vars == other.Meta.disassembled.mro.all_vars
                )

        Meta = M

    return Checker
