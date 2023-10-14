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
from ._extract import IsAnnotated, extract_annotation, extract_optional
from ._fields import (
    Field,
    fields_from_attrs,
    fields_from_class,
    fields_from_dataclasses,
)
from ._instance_check import InstanceCheck, InstanceCheckMeta, create_checkable
from ._score import Score

if tp.TYPE_CHECKING:
    from ..annotations import AdjustableCreator, AdjustableMeta
    from ..decorator import ConvertFunction
    from ._cache import TypeCache
    from ._type_tree import MRO


T = tp.TypeVar("T")
U = tp.TypeVar("U")


@attrs.define
class Type(tp.Generic[T]):
    """
    Wraps any object to provide an interface for introspection. Used to represent
    python types and type annotations.

    Usage is:

    .. code-block:: python

        import strcs

        type_cache = strcs.TypeCache()

        typ = strcs.Type.create(int, cache=type_cache)
        typ2 = strcs.Type.create(int | None, cache=type_cache)
        typ3 = type_cache.disassemble(int | None)
        typ4 = typ.disassemble(int | None)

        ...
    """

    class MissingType:
        score: Score

    class Missing(MissingType):
        """
        A representation for the absence of a type. (Used when understanding
        type variables)
        """

        score = Score(
            type_alias_name="",
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

    disassemble: "Disassembler" = attrs.field(
        init=False,
        default=attrs.Factory(lambda s: s.cache.disassemble, takes_self=True),
        repr=False,
        order=False,
        hash=False,
    )
    """Object for creating new Type classes without having to pass around the type cache"""

    original: object
    "The original object being wrapped"

    extracted: T
    "The extracted type if this object is optional or annotated or a ``typing.NewType`` object"

    type_alias: tp.NewType | None
    "The type alias used to reference this type if created with one"

    optional_inner: bool
    "True when the object is an annotated optional"

    optional_outer: bool
    "True when the object is an optional"

    annotated: IsAnnotated | None
    "The typing.Annotated object if this object is annotated"

    annotations: Sequence[object] | None
    "The metadata in the annotation if the object is a typing.Annotated"

    @classmethod
    def create(
        cls,
        typ: object,
        *,
        expect: type[U] | None = None,
        cache: "TypeCache",
    ) -> "Type[U]":
        """
        Used to create a :class:`strc.Type`.

        The ``expect`` parameter is purely for making it easier to say what type
        this is wrapping.
        """
        original = typ

        if isinstance(typ, cls):
            return tp.cast(Type[U], typ)

        if typ in cache:
            return cache[original]

        optional_inner = False
        optional_outer, typ = extract_optional(typ)
        extracted, annotated, annotations = extract_annotation(typ)

        if annotations is not None:
            optional_inner, extracted = extract_optional(extracted)
            typ = extracted

        if annotations is None and optional_outer:
            extracted, annotated, annotations = extract_annotation(typ)

        type_alias: tp.NewType | None = None
        if isinstance(extracted, tp.NewType):
            type_alias = extracted
            extracted = extracted.__supertype__

        constructor = tp.cast(tp.Callable[..., Type[U]], cls)

        made = constructor(
            cache=cache,
            original=original,
            extracted=extracted,
            type_alias=type_alias,
            optional_inner=optional_inner,
            optional_outer=optional_outer,
            annotated=annotated,
            annotations=annotations,
        )

        cache[original] = made

        return made

    def __hash__(self) -> int:
        """
        Wraps `hash(self.original)`
        """
        return hash(self.original)

    def __repr__(self) -> str:
        """
        Wraps `repr(self.original)`
        """
        return repr(self.original)

    def __eq__(self, o: object) -> tp.TypeGuard["Type"]:
        """
        The :class:`strcs.Type` object is equal to another object if:

        * ``o`` is :class:`strcs.Type.Missing`
        * ``o`` is a matching :class:`strcs.InstanceCheck`
        * ``o`` is a :class:`strcs.Type` with a matching ``original``
        * ``o`` equals ``self.original``
        * this is annotated and ``o`` is ``self.extracted``
        * this is optional and ``o`` is ``None``
        * ``o`` is a union and there is an overlap between the types represented
        by ``o`` and the relevant types on this.
        * ``o`` is one of the types relevant on this.
        """
        if o is Type.Missing:
            return True

        if issubclass(type(o), InstanceCheckMeta) and hasattr(o, "Meta"):
            o = o.Meta.disassembled

        if issubclass(type(o), Type) and hasattr(o, "original"):
            o = o.original

        other_alias: tp.NewType | None = None
        if isinstance(o, tp.NewType):
            other_alias = o
            o = other_alias.__supertype__

        if self.is_type_alias and other_alias is not None:
            return self.type_alias == other_alias

        if (
            o == self.original
            or (self.is_annotated and o == self.extracted)
            or (self.optional and o is None)
            or (self.mro.all_vars and o == self.origin)
            or (self.is_union and o in self.nonoptional_union_types)
        ):
            return True

        if type(o) in union_types:
            return len(set(tp.get_args(o)) - set(self.relevant_types)) == 0
        else:
            for part in self.relevant_types:
                disassembled = self.disassemble.typed(object, part)
                if o == disassembled.original:
                    return True
                elif disassembled.is_annotated and o == disassembled.extracted:
                    return True
                elif disassembled.optional and o is None:
                    return True
                elif disassembled.is_union and o in disassembled.nonoptional_union_types:
                    return True
                elif disassembled.mro.all_vars and o == disassembled.origin:
                    return True

            return False

    def for_display(self) -> str:
        """
        Return a string that will look close to how the developer writes
        the original object.
        """
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
        elif self.type_alias:
            # Honestly no idea why mypy doesn't think NewType has a __name__
            result = self.type_alias.__name__  # type: ignore[attr-defined]
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

        if self.annotations:
            items: list[str] = []
            for item in self.annotations:
                if isinstance(item, str):
                    items.append(json.dumps(item, default=repr))
                else:
                    items.append(str(item))
            result = f"Annotated[{result}, {', '.join(items)}]"

        if self.optional_outer:
            result = f"{result} | None"

        return result

    def __lt__(self, other: object) -> bool:
        """
        Complain if comparing against something that isn't a :class:`strcs.Type`
        and otherwise compare the `score`.
        """
        if not isinstance(other, Type):
            return NotImplemented

        return self.score < other.score

    def __lte__(self, other: object) -> bool:
        """
        Complain if comparing against something that isn't a :class:`strcs.Type`
        and otherwise compare the `score`.
        """
        if not isinstance(other, Type):
            return NotImplemented

        return self.score <= other.score

    def __gt__(self, other: object) -> bool:
        """
        Complain if comparing against something that isn't a :class:`strcs.Type`
        and otherwise compare the `score`.
        """
        if not isinstance(other, Type):
            return NotImplemented

        return self.score > other.score

    def __gte__(self, other: object) -> bool:
        """
        Complain if comparing against something that isn't a :class:`strcs.Type`
        and otherwise compare the `score`.
        """
        if not isinstance(other, Type):
            return NotImplemented

        return self.score >= other.score

    def reassemble(
        self, resolved: object, *, with_annotation: bool = True, with_optional: bool = True
    ) -> object:
        """
        Return a type annotation for the provided object using the optional
        and annotation on this instance.

        This takes into account both ``optional_inner`` and ``optional_outer``.

        This method takes in arguments to say whether to include annotation and
        optional or not.
        """
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
        """
        True if this object was annotated
        """
        return self.annotations is not None

    @property
    def is_type_alias(self) -> bool:
        """
        True if this object is a ``typing.NewType`` object
        """
        return self.type_alias is not None

    @property
    def optional(self) -> bool:
        """
        True if this object has either inner or outer optional
        """
        return self.optional_inner or self.optional_outer

    @memoized_property
    def mro(self) -> "MRO":
        """
        Return a :class:`strcs.MRO` instance from ``self.extracted``

        This is memoized.
        """
        from ._type_tree import MRO

        return MRO.create(self.extracted, type_cache=self.cache)

    @memoized_property
    def origin(self) -> type | tp.NewType:
        """
        if this type was created using a ``tp.NewType`` object, then that is returned.

        Otherwise if ``typing.get_origin(self.extracted)`` is a python type, then return that.

        Otherwise if ``self.extracted`` is a python type then return that.

        Otherwise return ``type(self.extracted)``

        This is memoized.
        """
        if self.type_alias:
            return self.type_alias

        origin = tp.get_origin(self.extracted)
        if isinstance(origin, type):
            return origin

        if isinstance(self.extracted, type):
            return self.extracted

        return type(self.extracted)

    @memoized_property
    def origin_type(self) -> type:
        """
        Gets the result of ``self.origin``. If the result is a ``tp.NewType`` then the
        type represented by that alias is returned, otherwise the origin is.

        This is memoized.
        """
        origin = self.origin
        if isinstance(origin, tp.NewType):
            return origin.__supertype__
        else:
            return origin

    @memoized_property
    def is_union(self) -> bool:
        """
        True if this type is a union. This works for the various ways it is
        possible to create a union typing annotation.

        This is memoized.
        """
        return tp.get_origin(self.extracted) in union_types

    @memoized_property
    def without_optional(self) -> object:
        """
        Return a :class:`strcs.Type` for this instance but without any optionals.

        This is memoized.
        """
        return self.reassemble(self.type_alias or self.extracted, with_optional=False)

    @memoized_property
    def without_annotation(self) -> object:
        """
        Return a :class:`strcs.Type` for this instance but without any annotation.

        This is memoized.
        """
        return self.reassemble(self.type_alias or self.extracted, with_annotation=False)

    @memoized_property
    def nonoptional_union_types(self) -> tuple["Type[object]", ...]:
        """
        Return a tuple of :class:`strcs.Type` objects represented by this object
        except for any ``None``.

        Return an empty tuple if this object is not already a union.

        This is memoized.
        """
        union: tuple["Type", ...] = ()
        if self.is_union:
            origins = tp.get_args(self.extracted)
            ds: list["Type"] = []
            for origin in origins:
                if origin is None:
                    continue
                ds.append(self.disassemble(origin))

            union = tuple(sorted(ds, key=lambda d: d.score, reverse=True))

        return union

    @memoized_property
    def score(self) -> Score:
        """
        Return a :class:``strcs.disassembled.Score`` instance for this.

        This is memoized.
        """
        return Score.create(self)

    @memoized_property
    def relevant_types(self) -> tp.Sequence[type]:
        """
        Return a sequence of python types relevant to this instance.

        This includes ``type(None)`` if this is optional.

        If this is a union, then returns all the types in that union, otherwise
        will contain only ``self.extracted`` if that is already a python type.

        This is memoized.
        """
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
        """
        Return if this is an object representing a class with fields.
        """
        return self.fields_getter is not None

    @property
    def fields_from(self) -> object:
        """
        Return the object to get fields from.

        If this is a union, return ``self.extracted``, otherwise return
        ``self.origin``
        """
        if self.is_union:
            return self.extracted
        else:
            return self.origin

    @memoized_property
    def fields_getter(self) -> tp.Callable[..., tp.Sequence[Field]] | None:
        """
        Return an appropriate function used to get fields from ``self.fields_from``.

        Will be :func:`strcs.disassemble.fields_from_attrs` if we are wrapping
        an attrs class.

        A :func:`strcs.disassemble.fields_from_dataclasses` if wrapping
        a dataclasses class.

        Or a :func:`strcs.disassemble.fields_from_class` if we are wrapping
        a python type that isn't :class:`strcs.NotSpecifiedMeta` or a builtin
        type.

        Otherwise ``None``

        This is memoized and all callables are returned as a partial passing
        in the type cache on this instance.
        """
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
        """
        Return a sequence of fields for this type without resolving any type vars.

        Will return an empty list if this Type is not for something with fields.

        This is memoized.
        """
        if self.fields_getter is None:
            return []

        return self.fields_getter(self.fields_from)

    @property
    def fields(self) -> Sequence[Field]:
        """
        Return a sequence of fields for this type after resolving any type vars.

        This property itself isn't memoized, but it's using a memoized property
        on ``self.mro``.

        Will return an empty list if this is a union.
        """
        if self.is_union:
            return []

        return self.mro.fields

    def find_generic_subtype(self, *want: type) -> Sequence["Type"]:
        """
        Match provided types with the filled type vars.

        This lets the user ask for the types on this typing annotation whilst
        also checking those types match expected types.
        """
        return self.mro.find_subtypes(*want)

    def is_type_for(self, instance: object) -> tp.TypeGuard[T]:
        """
        Whether this type represents the type for some object. Uses the
        ``isinstance`` check on the :class:`strcs.InstanceCheck` for this object.
        """
        return self.cache.comparer.isinstance(instance, self)

    def is_equivalent_type_for(self, value: object) -> tp.TypeGuard[T]:
        """
        Whether this type is equivalent to the passed in value.

        True if this type is the type for that value.

        Otherwise true if the passed in value is a subclass of this type using
        ``issubclass`` check on the :class:`strcs.InstanceCheck` for this object.
        """
        if self.is_type_for(value):
            return True

        return self.cache.comparer.issubclass(value, self.checkable)

    @memoized_property
    def ann(self) -> tp.Optional[tp.Union["AdjustableMeta[T]", "AdjustableCreator[T]"]]:
        """
        Return an object that fulfills :protocol:`strcs.AdjustableMeta` or
        :protocol:`strcs.AdjustableCreator` given any annotation on this type.

        If there is an annotation and it matches either those protocols already
        then it is returned as is.

        If it's a :class:`strcs.MetaAnnotation` or :class:`strcs.MergedMetaAnnotation`
        or a simple callable then a :class:`strcs.Ann` instance is made from it
        and that is returned.

        Note that currently only the first value in the annotation will be looked
        at.

        This is memoized.
        """
        from ..annotations import (
            AdjustableCreator,
            AdjustableMeta,
            Ann,
            MergedMetaAnnotation,
            MetaAnnotation,
        )

        ann: AdjustableMeta[T] | AdjustableCreator[T] | None = None
        if self.annotations is not None:
            # TODO: support multiple annotations
            annotation = self.annotations[0]

            if isinstance(annotation, AdjustableMeta):
                ann = annotation
            elif isinstance(annotation, (MetaAnnotation, MergedMetaAnnotation)):
                ann = Ann[T](annotation)
            elif isinstance(annotation, AdjustableCreator):
                ann = annotation
            elif callable(annotation):
                ann = Ann[T](creator=annotation)

        return ann

    def resolve_types(self, *, _resolved: set["Type"] | None = None):
        """
        Used by ``strcs.resolve_types`` to resolve any stringified type
        annotations on the original/extracted on this instance.

        This function will modify types such that they are annotated with
        objects rather than strings.
        """
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
        """
        Given a list of types to creators, choose the most appropriate function
        to create this type from.

        It will go through the list such that the most specific matches are looked
        at first.

        There are two passes of the options. In the first pass subclasses are
        not considered matches. In the second pass they are.
        """
        for want, func in sorted(options, key=lambda pair: pair[0], reverse=True):
            if self.cache.comparer.matches(self, want):
                return func

        for want, func in sorted(options, key=lambda pair: pair[0], reverse=True):
            if self.cache.comparer.matches(self, want, subclasses=True):
                return func

        return None

    @property
    def checkable_as_type(self) -> type[T]:
        """
        Return ``self.checkable``, but the return type of this function is a
        python type of the inner type represented by this :class:`strcs.Type`
        """
        return tp.cast(type[T], self.checkable)

    @memoized_property
    def checkable(self) -> type[InstanceCheck]:
        """
        Return an instance of :class:`strcs.InstanceCheck` for this instance.

        This is memoized.
        """
        return create_checkable(self)


class Disassembler(tp.Protocol):
    """
    Used to disassemble some type using an existing type cache
    """

    type_cache: "TypeCache"

    @tp.overload
    def __call__(self, typ: type[U]) -> "Type[U]":
        ...

    @tp.overload
    def __call__(self, typ: Type[U]) -> "Type[U]":
        ...

    @tp.overload
    def __call__(self, typ: object) -> "Type[object]":
        ...

    def __call__(self, typ: type[U] | object) -> "Type[U] | Type[object]":
        """
        Used to disassemble some type using an existing type cache

        Pass in expect to alter the type that the static type checker sees
        """

    def typed(self, expect: type[U], typ: object) -> "Type[U]":
        """
        Return a new :class:`strcs.Type` for the provided object using this
        type cache and the expected type.
        """
        ...
