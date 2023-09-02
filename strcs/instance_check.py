import abc
import typing as tp

from .standard import union_types

if tp.TYPE_CHECKING:
    from .disassemble import Type


class InstanceCheckMeta(type):
    pass


class InstanceCheck(abc.ABC):
    class Meta:
        typ: object
        original: object
        optional: bool
        union_types: tuple[type["InstanceCheck"]] | None
        disassembled: "Type"
        without_optional: object
        without_annotation: object


def create_checkable(disassembled: "Type") -> type[InstanceCheck]:
    extracted = disassembled.extracted
    origin = tp.get_origin(extracted)

    class Meta(InstanceCheck.Meta):
        typ = disassembled.origin
        original = disassembled.original
        optional = disassembled.optional
        without_optional = disassembled.without_optional
        without_annotation = disassembled.without_annotation

    Meta.disassembled = disassembled

    if origin in union_types:
        check_against = tuple(
            disassembled.disassemble(object, a).checkable for a in tp.get_args(extracted)
        )
        Meta.typ = extracted
        Meta.union_types = tp.cast(tuple[type[InstanceCheck]], check_against)
        Checker = _checker_union(disassembled, extracted, origin, check_against, Meta)
    else:
        Meta.union_types = None
        check_against_single: type | None = disassembled.origin
        if extracted is None:
            check_against_single = None
        Checker = _checker_single(disassembled, extracted, origin, check_against_single, Meta)

    if hasattr(extracted, "__args__"):
        Checker.__args__ = extracted.__args__  # type: ignore
    if hasattr(extracted, "__origin__"):
        Checker.__origin__ = extracted.__origin__  # type: ignore
    if hasattr(Checker.Meta.typ, "__attrs_attrs__"):
        Checker.__attrs_attrs__ = Checker.Meta.typ.__attrs_attrs__  # type:ignore
    if hasattr(Checker.Meta.typ, "__dataclass_fields__"):
        Checker.__dataclass_fields__ = Checker.Meta.typ.__dataclass_fields__  # type:ignore

    return Checker


def _checker_union(
    disassembled: "Type",
    extracted: object,
    origin: object,
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
            return hash(extracted)

        @property  # type:ignore
        def __class__(self) -> type:
            return type(extracted)

    class CombinedMeta(CheckerMeta, abc.ABCMeta):
        pass

    class Checker(InstanceCheck, metaclass=CombinedMeta):
        def __new__(mcls, *args, **kwargs):
            raise ValueError(f"Cannot instantiate a union type: {check_against}")

        def __hash__(self) -> int:
            return hash(check_against)

        @classmethod
        def __subclasshook__(cls, C: type) -> bool:
            if C == CombinedMeta:
                return True

            if hasattr(C, "Meta") and issubclass(C.Meta, InstanceCheck.Meta):
                if isinstance(C.Meta.typ, type):
                    C = C.Meta.typ
            return issubclass(C, tuple(check_against))

        Meta = M

    return Checker


def _checker_single(
    disassembled: "Type",
    extracted: object,
    origin: object,
    check_against: object | None,
    M: type[InstanceCheck.Meta],
) -> type[InstanceCheck]:
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
            return hash(extracted)

        @property  # type:ignore
        def __class__(self) -> type:
            return type(extracted)

    class CombinedMeta(CheckerMeta, abc.ABCMeta):
        pass

    class Checker(InstanceCheck, metaclass=CombinedMeta):
        def __new__(mcls, *args, **kwargs):
            return check_against(*args, **kwargs)

        def __hash__(self) -> int:
            return hash(check_against)

        @classmethod
        def __subclasshook__(cls, C: type) -> bool:
            if C == CombinedMeta:
                return True

            if not isinstance(check_against, type):
                return False

            if hasattr(C, "Meta") and issubclass(C.Meta, InstanceCheck.Meta):
                if isinstance(C.Meta.typ, type):
                    C = C.Meta.typ
            return issubclass(C, check_against)

        Meta = M

    return Checker
