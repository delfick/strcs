import abc
import builtins
import functools
import inspect
import itertools
import operator
import sys
import types
import typing as tp
from dataclasses import MISSING
from dataclasses import fields as dataclass_fields
from dataclasses import is_dataclass

import attrs
from attrs import NOTHING, Attribute, define
from attrs import fields as attrs_fields
from attrs import has as attrs_has

from .not_specified import NotSpecifiedMeta

T = tp.TypeVar("T")
builtin_types = [v for v in vars(builtins).values() if isinstance(v, type)]


@define
class Default:
    value: object | None

    def __call__(self) -> object | None:
        return self.value


def kind_name(kind: int) -> str:
    known = (
        inspect.Parameter.KEYWORD_ONLY,
        inspect.Parameter.VAR_POSITIONAL,
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
        inspect.Parameter.POSITIONAL_ONLY,
        inspect.Parameter.KEYWORD_ONLY,
        inspect.Parameter.VAR_KEYWORD,
    )

    for k in known:
        if k.value == kind:
            return f"'{k.description}'"

    return "<UNKNOWN_KIND>"


@define
class _Field:
    name: str
    type: object
    kind: int = attrs.field(default=inspect.Parameter.POSITIONAL_OR_KEYWORD.value, repr=kind_name)
    default: tp.Callable[[], object | None] | None = attrs.field(default=None)

    def with_replaced_type(self, typ: object) -> "_Field":
        return self.__class__(name=self.name, type=typ, kind=self.kind, default=self.default)

    @kind.validator
    def check_kind(self, attribute: Attribute, value: object) -> None:
        allowed = (
            inspect.Parameter.KEYWORD_ONLY,
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.KEYWORD_ONLY,
            inspect.Parameter.VAR_KEYWORD,
        )
        if value not in [a.value for a in allowed]:
            raise ValueError(
                f"Only allow parameter kinds. Got {value}, want one of {', '.join([f'{a.value} ({a.description})' for a in allowed])}"
            )


def fields_from_class(typ: type) -> tp.Sequence[_Field]:
    result: list[_Field] = []
    signature = inspect.signature(typ)
    for name, param in list(signature.parameters.items()):
        field_type = param.annotation
        if param.annotation is inspect.Parameter.empty:
            field_type = object

        if param.kind in (inspect.Parameter.VAR_KEYWORD, inspect.Parameter.VAR_POSITIONAL):
            name = ""

        dflt: tp.Callable[[], object | None] | None = None
        if param.default is not inspect.Parameter.empty:
            dflt = Default(param.default)
        result.append(_Field(name=name, default=dflt, kind=param.kind.value, type=field_type))

    return result


def fields_from_attrs(typ: type) -> tp.Sequence[_Field]:
    result: list[_Field] = []
    for field in attrs_fields(typ):
        if not field.init:
            continue

        field_type = field.type
        if field_type is None:
            field_type = object

        kind = inspect.Parameter.POSITIONAL_OR_KEYWORD.value
        if field.kw_only:
            kind = inspect.Parameter.KEYWORD_ONLY.value

        dflt: tp.Callable[[], object | None] | None = None
        if hasattr(field.default, "factory") and callable(field.default.factory):
            if not field.default.takes_self:
                dflt = field.default.factory

        elif field.default is not NOTHING:
            dflt = Default(field.default)

        if sys.version_info >= (3, 11) and field.alias is not None:
            name = field.alias
        else:
            name = field.name
            if name.startswith("_"):
                name = name[1:]

        if name.startswith(f"{typ.__name__}_"):
            name = name[len(f"{typ.__name__}_") + 1 :]

        result.append(
            _Field(
                name=name,
                default=dflt,
                kind=kind,
                type=field_type,
            )
        )

    return result


def fields_from_dataclasses(typ: type) -> tp.Sequence[_Field]:
    result: list[_Field] = []
    for field in dataclass_fields(typ):
        if not field.init:
            continue

        field_type = field.type
        if field_type is None:
            field_type = object

        kind = inspect.Parameter.POSITIONAL_OR_KEYWORD.value
        if field.kw_only:
            kind = inspect.Parameter.KEYWORD_ONLY.value

        dflt: tp.Callable[[], object | None] | None = None
        if field.default is not MISSING:
            dflt = Default(field.default)

        if field.default_factory is not MISSING:
            dflt = field.default_factory

        name = field.name
        result.append(_Field(name=name, default=dflt, kind=kind, type=field_type))
    return result


class memoized_property(tp.Generic[T]):
    class Empty:
        pass

    def __init__(self, func: tp.Callable[..., T]):
        self.func = func
        self.name = func.__name__
        self.__doc__ = func.__doc__
        self.cache_name = "_{0}".format(self.name)

    def __get__(self, instance: object = None, owner: object = None) -> T:
        if instance is None:
            return tp.cast(T, self)

        if getattr(instance, self.cache_name, self.Empty) is self.Empty:
            setattr(instance, self.cache_name, self.func(instance))
        return getattr(instance, self.cache_name)

    def __set__(self, instance, value):
        setattr(instance, self.cache_name, value)

    def __delete__(self, instance):
        if hasattr(instance, self.cache_name):
            delattr(instance, self.cache_name)


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


def extract_optional(typ: object) -> tuple[bool, object]:
    optional = False
    if tp.get_origin(typ) in (types.UnionType, tp.Union):
        if type(None) in tp.get_args(typ):
            optional = True

            remaining = tuple(a for a in tp.get_args(typ) if a not in (types.NoneType,))
            if len(remaining) == 1:
                typ = remaining[0]
            else:
                typ = functools.reduce(operator.or_, remaining)

    return optional, typ


def extract_annotation(typ: object) -> tuple[object, IsAnnotated | None, object | None]:
    if IsAnnotated.has(typ):
        return typ.__args__[0], typ, typ.__metadata__[0]
    else:
        return typ, None, None


class InstanceCheckMeta(type):
    pass


class InstanceCheck(abc.ABC):
    class Meta:
        typ: object
        original: object
        optional: bool
        without_optional: object
        without_annotation: object


@define
class Disassembled:
    original: object
    extracted: object
    optional_inner: bool
    optional_outer: bool
    annotated: IsAnnotated | None
    annotation: object | None

    @classmethod
    def create(cls, typ: object) -> "Disassembled":
        original = typ
        optional_inner = False
        optional_outer, typ = extract_optional(typ)
        extracted, annotated, annotation = extract_annotation(typ)

        if annotation is not None:
            optional_inner, extracted = extract_optional(extracted)
            typ = extracted

        if annotation is None and optional_outer:
            extracted, annotated, annotation = extract_annotation(typ)

        return Disassembled(
            original=original,
            extracted=extracted,
            optional_inner=optional_inner,
            optional_outer=optional_outer,
            annotated=annotated,
            annotation=annotation,
        )

    def reassemble(
        self, resolved: object, *, with_annotation: bool = True, with_optional: bool = True
    ) -> object:
        if self.optional_inner and with_optional:
            resolved = functools.reduce(operator.or_, (resolved, None))
        if self.annotated is not None and with_annotation:
            resolved = self.annotated.copy_with((resolved,))
        if self.optional_outer and with_optional:
            if with_annotation or not self.optional_inner:
                resolved = functools.reduce(operator.or_, (resolved, None))

        return resolved

    @property
    def is_annotated(self) -> bool:
        return self.annotation is not None

    @property
    def optional(self) -> bool:
        return self.optional_inner or self.optional_outer

    @memoized_property
    def origin_or_type(self) -> object:
        orig = tp.get_origin(self.extracted)
        if not isinstance(orig, type) and orig not in (types.UnionType, tp.Union):
            return self.extracted
        else:
            return orig

    _origin_or_type: object = attrs.field(init=False)

    @memoized_property
    def without_optional(self) -> object:
        return self.reassemble(self.extracted, with_optional=False)

    _without_optional: object = attrs.field(init=False)

    @memoized_property
    def without_annotation(self) -> object:
        return self.reassemble(self.extracted, with_annotation=False)

    _without_annotation: object = attrs.field(init=False)

    @memoized_property
    def generics(self) -> tuple[dict[tp.TypeVar, type], list[tp.TypeVar]]:
        typevar_map: dict[tp.TypeVar, type] = {}
        typevars: list[tp.TypeVar] = []

        for base in getattr(self.origin_or_type, "__orig_bases__", ()):
            typevars.extend(tp.get_args(base))

        for tv, ag in zip(typevars, tp.get_args(self.extracted)):
            typevar_map[tv] = ag

        return typevar_map, typevars

    _generics: tuple[dict[tp.TypeVar, type], list[tp.TypeVar]] = attrs.field(init=False)

    @property
    def has_fields(self) -> bool:
        return self.fields_getter is not None

    @memoized_property
    def fields_from(self) -> object:
        origin = self.origin_or_type
        if (
            not isinstance(self.extracted, type)
            or (not attrs_has(self.extracted) and not is_dataclass(self.extracted))
            and origin
        ):
            if origin not in (types.UnionType, tp.Union):
                return origin

        return self.extracted

    _fields_from: object = attrs.field(init=False)

    @memoized_property
    def fields_getter(self) -> tp.Callable[..., tp.Sequence[_Field]] | None:
        if isinstance(self.fields_from, type) and attrs_has(self.fields_from):
            return fields_from_attrs
        elif is_dataclass(self.fields_from):
            return fields_from_dataclasses
        elif (
            tp.get_origin(self.extracted) is None
            and isinstance(self.extracted, type)
            and self.extracted is not NotSpecifiedMeta
            and self.extracted not in builtin_types
        ):
            return fields_from_class

        return None

    _fields_getter: tp.Callable[..., tp.Sequence[_Field]] | None = attrs.field(init=False)

    @memoized_property
    def fields(self) -> list[_Field]:
        if self.fields_getter is None:
            return []

        fields: list[_Field] = []

        typevar_map, typevars = self.generics
        for field in self.fields_getter(self.fields_from):
            field_type = field.type
            if isinstance(field_type, tp.TypeVar):
                field_type = typevar_map.get(field_type, object)
            fields.append(field.with_replaced_type(field_type))

        return fields

    _fields: list[_Field] = attrs.field(init=False)

    def find_generic_subtype(self, *want: type) -> list[type]:
        result: list[type] = []
        typevar_map, typevars = self.generics

        for tv, wa in itertools.zip_longest(typevars, want):
            if wa is None:
                break
            if tv is None:
                raise ValueError(
                    f"The type has less typevars ({len(typevars)}) than wanted ({len(want)})"
                )

            typ = typevar_map[tv]
            if not issubclass(typ, want):
                raise ValueError(
                    f"The concrete type {typ} is not a subclass of what was asked for {wa}"
                )

            result.append(typ)

        return result

    def is_type_for(self, instance: object) -> tp.TypeGuard[T]:
        return isinstance(instance, self.checkable)

    def is_equivalent_type_for(
        self, value: object, make_subclass_of: tp.Callable[[], type] | None = None
    ) -> tp.TypeGuard[T]:
        if self.is_type_for(value):
            return True

        if make_subclass_of is None:
            subclass_of = Disassembled.create(type(value)).checkable
        else:
            subclass_of = make_subclass_of()
        return issubclass(subclass_of, self.checkable)

    @memoized_property
    def checkable(self) -> type[InstanceCheck]:
        disassembled: Disassembled = self
        extracted = disassembled.extracted
        origin = tp.get_origin(extracted)

        class Meta(InstanceCheck.Meta):
            typ = disassembled.origin_or_type
            original = disassembled.original
            optional = disassembled.optional
            without_optional = disassembled.without_optional
            without_annotation = disassembled.without_annotation

        if origin is not None and origin in (types.UnionType, tp.Union):
            check_against = tuple(Disassembled.create(a).checkable for a in tp.get_args(extracted))
            Meta.typ = extracted
            Checker = self._checker_union(extracted, origin, check_against, Meta)
        else:
            Checker = self._checker_single(extracted, origin, disassembled.origin_or_type, Meta)

        if hasattr(extracted, "__args__"):
            Checker.__args__ = extracted.__args__  # type: ignore
        if hasattr(extracted, "__origin__"):
            Checker.__origin__ = extracted.__origin__  # type: ignore
        if hasattr(Checker.Meta.typ, "__attrs_attrs__"):
            Checker.__attrs_attrs__ = Checker.Meta.typ.__attrs_attrs__  # type:ignore
        if hasattr(Checker.Meta.typ, "__dataclass_fields__"):
            Checker.__dataclass_fields__ = Checker.Meta.typ.__dataclass_fields__  # type:ignore

        return Checker

    _checkable: type[InstanceCheck] = attrs.field(init=False)

    def _checker_union(
        self,
        extracted: object,
        origin: object,
        check_against: tp.Sequence[type],
        M: type[InstanceCheck.Meta],
    ) -> type[InstanceCheck]:
        disassembled = self

        reprstr = repr(functools.reduce(operator.or_, check_against))

        class CheckerMeta(InstanceCheckMeta):
            def __repr__(self) -> str:
                return reprstr

            def __instancecheck__(self, obj: object) -> bool:
                return (obj is None and disassembled.optional) or any(
                    isinstance(obj, tp.cast(type, ch)) for ch in check_against
                )

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
                return any(issubclass(C, ch) for ch in check_against)

            Meta = M

        return Checker

    def _checker_single(
        self,
        extracted: object,
        origin: object,
        check_against: object,
        M: type[InstanceCheck.Meta],
    ) -> type[InstanceCheck]:
        disassembled = self

        class CheckerMeta(InstanceCheckMeta):
            def __repr__(self) -> str:
                return repr(check_against)

            def __instancecheck__(self, obj: object) -> bool:
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