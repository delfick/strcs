import abc
import builtins
import collections
import collections.abc
import functools
import inspect
import itertools
import json
import operator
import sys
import types
import typing as tp
from dataclasses import MISSING
from dataclasses import fields as dataclass_fields
from dataclasses import is_dataclass

import attrs
import cattrs
from attrs import NOTHING, Attribute, define
from attrs import fields as attrs_fields
from attrs import has as attrs_has

from .hints import resolve_types
from .memoized_property import memoized_property
from .not_specified import NotSpecified, NotSpecifiedMeta

if tp.TYPE_CHECKING:
    from .annotations import Ann
    from .decorator import ConvertFunction
    from .type_tree import MRO


T = tp.TypeVar("T")
U = tp.TypeVar("U")
builtin_types = [v for v in vars(builtins).values() if isinstance(v, type)]
union_types: list[object] = [type(tp.Union[str, int]), type(str | int), types.UnionType, tp.Union]


def _get_generic_super() -> type:
    class _G(tp.Generic[T]):
        one: T

    bases = getattr(_G, "__orig_bases__", None)
    assert isinstance(bases, tuple) and len(bases) > 0
    ret = tp.get_origin(bases[0])
    assert isinstance(ret, type)
    return ret


generic_super = _get_generic_super()


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
class Field(tp.Generic[T]):
    name: str
    owner: object
    type: T
    kind: int = attrs.field(default=inspect.Parameter.POSITIONAL_OR_KEYWORD.value, repr=kind_name)
    default: tp.Callable[[], object | None] | None = attrs.field(default=None)

    def with_replaced_type(self, typ: U) -> "Field[U]":
        return Field[U](
            name=self.name, owner=self.owner, type=typ, kind=self.kind, default=self.default
        )

    def clone(self) -> "Field[T]":
        return self.with_replaced_type(self.type)

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


def fields_from_class(typ: type) -> tp.Sequence[Field]:
    result: list[Field] = []
    try:
        signature = inspect.signature(typ)
    except ValueError:
        return result

    for name, param in list(signature.parameters.items()):
        field_type = param.annotation
        if param.annotation is inspect.Parameter.empty:
            field_type = object

        if param.kind in (inspect.Parameter.VAR_KEYWORD, inspect.Parameter.VAR_POSITIONAL):
            name = ""

        dflt: tp.Callable[[], object | None] | None = None
        if param.default is not inspect.Parameter.empty:
            dflt = Default(param.default)
        result.append(
            Field(name=name, owner=typ, default=dflt, kind=param.kind.value, type=field_type)
        )

    return result


def fields_from_attrs(typ: type) -> tp.Sequence[Field]:
    result: list[Field] = []
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
            Field(
                name=name,
                owner=typ,
                default=dflt,
                kind=kind,
                type=field_type,
            )
        )

    return result


def fields_from_dataclasses(typ: type) -> tp.Sequence[Field]:
    result: list[Field] = []
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
        result.append(Field(name=name, owner=typ, default=dflt, kind=kind, type=field_type))
    return result


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


@define
class Type(tp.Generic[T]):
    class Missing:
        pass

    cache: "TypeCache" = attrs.field(repr=False)

    _memoized_cache: dict[str, object] = attrs.field(
        init=False, factory=lambda: {}, repr=False, order=False, hash=False
    )

    original: object
    extracted: T
    optional_inner: bool
    optional_outer: bool
    annotated: IsAnnotated | None
    annotation: object | None

    @classmethod
    def create(
        cls,
        typ: object,
        *,
        expect: type[U] | None = None,
        cache: "TypeCache",
    ) -> "Type[U]":
        original = typ

        if isinstance(typ, cls):
            return tp.cast(Type[U], typ)

        if typ in cache:
            return cache[original]

        optional_inner = False
        optional_outer, typ = extract_optional(typ)
        extracted, annotated, annotation = extract_annotation(typ)

        if annotation is not None:
            optional_inner, extracted = extract_optional(extracted)
            typ = extracted

        if annotation is None and optional_outer:
            extracted, annotated, annotation = extract_annotation(typ)

        constructor = tp.cast(tp.Callable[..., Type[U]], cls)

        made = constructor(
            cache=cache,
            original=original,
            extracted=extracted,
            optional_inner=optional_inner,
            optional_outer=optional_outer,
            annotated=annotated,
            annotation=annotation,
        )

        cache[original] = made

        return made

    def __hash__(self) -> int:
        return hash(self.original)

    def __repr__(self) -> str:
        return repr(self.original)

    def __eq__(self, o: object) -> tp.TypeGuard["Type"]:
        if o is Type.Missing:
            return True

        if isinstance(o, InstanceCheck) and hasattr(o, "Meta"):
            o = o.Meta.disassembled

        if isinstance(o, Type):
            o = o.original

        if (
            o == self.original
            or (self.is_annotated and o == self.extracted)
            or (self.optional and o is None)
        ):
            return True

        if type(o) in union_types:
            return len(set(tp.get_args(o)) - set(self.relevant_types)) == 0
        else:
            return o in self.relevant_types

    def for_display(self) -> str:
        if self.is_union:
            parts: list[str] = []
            for part in self.nonoptional_union_types:
                parts.append(part.for_display())
            result = " | ".join(parts)
        elif self.mro.typevars:
            result = repr(self.extracted)
            if hasattr(self.extracted, "__name__"):
                result = self.extracted.__name__

            if signature := self.mro.signature_for_display:
                result = f"{result}[{signature}]"
        else:
            want: object = self.original
            if self.annotated or self.optional:
                want = self.extracted

            if hasattr(want, "__name__"):
                result = want.__name__
            else:
                result = repr(want)

        if self.optional_inner:
            result = f"{result} | None"

        if self.annotated:
            if isinstance(self.annotation, str):
                annotation = json.dumps(self.annotation, default=repr)
            else:
                annotation = str(self.annotation)
            result = f"Annotated[{result}, {annotation}]"

        if self.optional_outer:
            result = f"{result} | None"

        return result

    def disassemble(self, expect: type[U], typ: object) -> "Type[U]":
        return Type.create(typ, expect=expect, cache=self.cache)

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
    def mro(self) -> "MRO":
        from .type_tree import MRO

        return MRO.create(self.extracted, type_cache=self.cache)

    @memoized_property
    def origin(self) -> type:
        origin = tp.get_origin(self.extracted)
        if isinstance(origin, type):
            return origin

        if isinstance(self.extracted, type):
            return self.extracted

        return type(self.extracted)

    @memoized_property
    def is_union(self) -> bool:
        return tp.get_origin(self.extracted) in union_types

    @memoized_property
    def without_optional(self) -> object:
        return self.reassemble(self.extracted, with_optional=False)

    @memoized_property
    def without_annotation(self) -> object:
        return self.reassemble(self.extracted, with_annotation=False)

    @memoized_property
    def nonoptional_union_types(self) -> tuple["Type", ...]:
        union: tuple["Type", ...] = ()
        if self.is_union:
            origins = tp.get_args(self.extracted)
            ds: list["Type"] = []
            for origin in origins:
                if origin is None:
                    continue
                ds.append(self.disassemble(object, origin))

            # TODO: order the types correctly
            union = tuple(sorted(ds, key=lambda d: str(d), reverse=True))

        return union

    @memoized_property
    def relevant_types(self) -> tp.Sequence[type]:
        relevant: list[type] = []
        if self.optional:
            relevant.append(type(None))

        if self.is_union:
            relevant.extend(tp.get_args(self.extracted))
        elif isinstance(self.extracted, type):
            relevant.append(self.extracted)

        return relevant

    @memoized_property
    def generics(self) -> tuple[dict[tp.TypeVar, type], list[tp.TypeVar]]:
        typevar_map: dict[tp.TypeVar, type] = {}
        typevars: list[tp.TypeVar] = []

        for base in getattr(self.origin, "__orig_bases__", ()):
            typevars.extend(tp.get_args(base))

        for tv, ag in zip(typevars, tp.get_args(self.extracted)):
            typevar_map[tv] = ag

        return typevar_map, typevars

    @property
    def has_fields(self) -> bool:
        return self.fields_getter is not None

    @memoized_property
    def fields_from(self) -> object:
        if self.is_union:
            return self.extracted

        origin = self.origin
        if (
            not isinstance(self.extracted, type)
            or (not attrs_has(self.extracted) and not is_dataclass(self.extracted))
            and origin
        ):
            if origin not in union_types:
                return origin

        return self.extracted

    @memoized_property
    def fields_getter(self) -> tp.Callable[..., tp.Sequence[Field]] | None:
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

    @memoized_property
    def fields(self) -> list[Field]:
        if self.fields_getter is None:
            return []

        fields: list[Field] = []

        typevar_map, typevars = self.generics
        for field in self.fields_getter(self.fields_from):
            field_type = field.type
            if isinstance(field_type, tp.TypeVar):
                field_type = typevar_map.get(field_type, object)
            fields.append(field.with_replaced_type(field_type))

        return fields

    @memoized_property
    def typed_fields(self) -> list[Field]:
        res: list[Field] = []
        for field in self.fields:
            if field.type is None:
                res.append(field.with_replaced_type(field.type))
            else:
                res.append(field.with_replaced_type(self.disassemble(field.type, field.type)))
        return res

    def find_generic_subtype(self, *want: type) -> list["Type"]:
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

        return [self.disassemble(object, typ) for typ in result]

    def is_type_for(self, instance: object) -> tp.TypeGuard[T]:
        return isinstance(instance, self.checkable)

    def is_equivalent_type_for(self, value: object) -> tp.TypeGuard[T]:
        if self.is_type_for(value):
            return True

        if isinstance(value, type):
            subclass_of = value
        else:
            subclass_of = self.disassemble(object, type(value)).checkable
        return issubclass(subclass_of, self.checkable)

    @memoized_property
    def ann(self) -> tp.Optional["Ann[T]"]:
        from .annotations import AdjustableMeta, Ann, AnnBase, Annotation

        ann: Ann[T] | None = None
        if self.annotation is not None and (
            isinstance(self.annotation, (Ann, Annotation)) or callable(self.annotation)
        ):

            if isinstance(self.annotation, Ann):
                ann = self.annotation
            elif isinstance(self.annotation, (Annotation, AdjustableMeta)):
                ann = AnnBase[T](self.annotation)
            elif callable(self.annotation):
                ann = AnnBase[T](creator=self.annotation)

        return ann

    def resolve_types(self, *, _resolved: set["Type"] | None = None):
        if _resolved is None:
            _resolved = set()

        if self in _resolved:
            return
        _resolved.add(self)

        if isinstance(self.original, type):
            resolve_types(self.original, type_cache=self.cache)
        if isinstance(self.extracted, type):
            resolve_types(self.extracted, type_cache=self.cache)

        args = getattr(self.extracted, "__args__", None)
        if args:
            for arg in args:
                if isinstance(arg, type):
                    resolve_types(arg, type_cache=self.cache)

        for field in self.typed_fields:
            field.type.resolve_types(_resolved=_resolved)

    def func_from(
        self, options: list[tuple["Type", "ConvertFunction"]]
    ) -> tp.Optional["ConvertFunction"]:
        for want, func in options:
            if want in (self.original, self.extracted) or want == self:
                return func

        for want, func in options:
            if issubclass(self.checkable, want.checkable):
                return func

        if not isinstance(self.origin, type):
            return None

        for want, func in options:
            if want is self.origin:
                return func

        for want, func in options:
            if issubclass(self.origin, want.checkable):
                return func

        return None

    def fill(self, res: object) -> tp.Mapping[str, object]:
        if res is NotSpecified:
            res = {}

        if not isinstance(res, collections.abc.Mapping):
            raise ValueError(f"Can only fill mappings, got {type(res)}")

        if isinstance(res, dict):
            for field in self.typed_fields:
                if field.type is not None and field.name not in res:
                    if field.type.is_annotated or field.type.has_fields:
                        res[field.name] = NotSpecified

        return res

    def convert(self, res: object, converter: cattrs.Converter) -> T:
        if self.optional and res is None:
            return tp.cast(T, None)

        if not callable(self.extracted):
            raise TypeError(f"Unsure how to instantiate a {type(self.extracted)}: {self.extracted}")

        res = self.fill(res)

        conv_obj: dict[str, object] = {}
        for field in self.typed_fields:
            name = field.name

            if name not in res:
                continue

            val = res[name]
            if name.startswith("_"):
                name = name[1:]

            attribute = tp.cast(
                attrs.Attribute,
                Field(name=field.name, owner=field.owner, type=tp.cast(type, field.type.original)),
            )
            conv_obj[name] = converter._structure_attribute(attribute, val)

        return self.extracted(**conv_obj)

    @property
    def checkable_as_type(self) -> type[T]:
        return tp.cast(type[T], self.checkable)

    @memoized_property
    def checkable(self) -> type[InstanceCheck]:
        disassembled: Type = self
        extracted = disassembled.extracted
        origin = tp.get_origin(extracted)

        class Meta(InstanceCheck.Meta):
            typ = disassembled.origin
            original = disassembled.original
            optional = disassembled.optional
            without_optional = disassembled.without_optional
            without_annotation = disassembled.without_annotation

        Meta.disassembled = self

        if origin in union_types:
            check_against = tuple(
                self.disassemble(object, a).checkable for a in tp.get_args(extracted)
            )
            Meta.typ = extracted
            Meta.union_types = tp.cast(tuple[type[InstanceCheck]], check_against)
            Checker = self._checker_union(extracted, origin, check_against, Meta)
        else:
            Meta.union_types = None
            check_against_single: type | None = disassembled.origin
            if extracted is None:
                check_against_single = None
            Checker = self._checker_single(extracted, origin, check_against_single, Meta)

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

        reprstr = " | ".join(repr(c) for c in check_against)

        class CheckerMeta(InstanceCheckMeta):
            def __repr__(self) -> str:
                return reprstr

            def __instancecheck__(self, obj: object) -> bool:
                return (obj is None and disassembled.optional) or isinstance(
                    obj, tuple(check_against)
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
                return issubclass(C, tuple(check_against))

            Meta = M

        return Checker

    def _checker_single(
        self,
        extracted: object,
        origin: object,
        check_against: object | None,
        M: type[InstanceCheck.Meta],
    ) -> type[InstanceCheck]:
        disassembled = self

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


class TypeCache(collections.abc.MutableMapping[object, "Type"]):
    def __init__(self):
        self.cache = {}

    def key(self, o: object) -> tuple[type, object]:
        return (type(o), o)

    def __getitem__(self, k: object) -> Type:
        return self.cache[self.key(k)]

    def __setitem__(self, k: object, v: Type) -> None:
        try:
            hash(k)
        except TypeError:
            return
        else:
            self.cache[self.key(k)] = v

    def __delitem__(self, k: object) -> None:
        del self.cache[self.key(k)]

    def __contains__(self, k: object) -> bool:
        try:
            hash(k)
        except TypeError:
            return False
        else:
            return self.key(k) in self.cache

    def __iter__(self) -> tp.Iterator[object]:
        return iter(self.cache)

    def __len__(self) -> int:
        return len(self.cache)

    def clear(self) -> None:
        self.cache.clear()
