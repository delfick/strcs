import dataclasses
import functools
import json
import operator
import typing as tp
from collections.abc import Sequence
from functools import partial

import attrs

from ..hints import resolve_types
from ..memoized_property import memoized_property
from ..not_specified import NotSpecifiedMeta
from ..standard import builtin_types, union_types
from .extract import IsAnnotated, extract_annotation, extract_optional
from .fields import Field, fields_from_attrs, fields_from_class, fields_from_dataclasses
from .instance_check import InstanceCheck, create_checkable
from .score import Score

if tp.TYPE_CHECKING:
    from ..annotations import AdjustableCreator, AdjustableMeta
    from ..decorator import ConvertFunction
    from .cache import TypeCache
    from .type_tree import MRO


T = tp.TypeVar("T")
U = tp.TypeVar("U")


@attrs.define
class Type(tp.Generic[T]):
    class MissingType:
        score: Score

    class Missing(MissingType):
        score = Score(
            union=(),
            annotated=False,
            typevars=(),
            typevars_filled=(),
            optional=False,
            origin_mro=(),
        )

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

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Type):
            return NotImplemented

        return self.score < other.score

    def __lte__(self, other: object) -> bool:
        if not isinstance(other, Type):
            return NotImplemented

        return self.score <= other.score

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, Type):
            return NotImplemented

        return self.score > other.score

    def __gte__(self, other: object) -> bool:
        if not isinstance(other, Type):
            return NotImplemented

        return self.score >= other.score

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

            union = tuple(sorted(ds, key=lambda d: d.score, reverse=True))

        return union

    @memoized_property
    def score(self) -> Score:
        return Score.create(self)

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
            or (not attrs.has(self.extracted) and not dataclasses.is_dataclass(self.extracted))
            and origin
        ):
            if origin not in union_types:
                return origin

        return self.extracted

    @memoized_property
    def fields_getter(self) -> tp.Callable[..., tp.Sequence[Field]] | None:
        if isinstance(self.fields_from, type) and attrs.has(self.fields_from):
            return partial(fields_from_attrs, self.cache)
        elif dataclasses.is_dataclass(self.fields_from):
            return partial(fields_from_dataclasses, self.cache)
        elif (
            tp.get_origin(self.extracted) is None
            and isinstance(self.extracted, type)
            and self.extracted is not NotSpecifiedMeta
            and self.extracted not in builtin_types
        ):
            return partial(fields_from_class, self.cache)

        return None

    @memoized_property
    def raw_fields(self) -> Sequence[Field]:
        if self.fields_getter is None:
            return []

        return self.fields_getter(self.fields_from)

    @property
    def fields(self) -> Sequence[Field]:
        if self.is_union:
            return []

        return self.mro.fields

    def find_generic_subtype(self, *want: type) -> Sequence["Type"]:
        return self.mro.find_subtypes(*want)

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
    def ann(self) -> tp.Optional[tp.Union["AdjustableMeta[T]", "AdjustableCreator[T]"]]:
        from ..annotations import (
            AdjustableCreator,
            AdjustableMeta,
            Ann,
            MergedMetaAnnotation,
            MetaAnnotation,
        )

        ann: AdjustableMeta[T] | AdjustableCreator[T] | None = None
        if self.annotation is not None:
            if isinstance(self.annotation, AdjustableMeta):
                ann = self.annotation
            elif isinstance(self.annotation, (MetaAnnotation, MergedMetaAnnotation)):
                ann = Ann[T](self.annotation)
            elif isinstance(self.annotation, AdjustableCreator):
                ann = self.annotation
            elif callable(self.annotation):
                ann = Ann[T](creator=self.annotation)

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

        for field in self.fields:
            field.disassembled_type.resolve_types(_resolved=_resolved)

    def func_from(
        self, options: list[tuple["Type", "ConvertFunction"]]
    ) -> tp.Optional["ConvertFunction"]:
        for want, func in sorted(options, key=lambda pair: pair[0], reverse=True):
            if self.checkable.matches(want.checkable):
                return func

        for want, func in sorted(options, key=lambda pair: pair[0], reverse=True):
            if self.checkable.matches(want.checkable, subclasses=True):
                return func

        return None

    @property
    def checkable_as_type(self) -> type[T]:
        return tp.cast(type[T], self.checkable)

    @memoized_property
    def checkable(self) -> type[InstanceCheck]:
        return create_checkable(self)
