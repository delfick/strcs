import collections
import dataclasses
import itertools
import typing as tp

import attrs
import cattrs
from attrs import define
from attrs import has as attrs_has

from .hints import resolve_types
from .meta import Meta, extract_type
from .not_specified import NotSpecified, NotSpecifiedMeta

if tp.TYPE_CHECKING:
    from .decorator import CreateArgs
    from .register import CreateRegister


T = tp.TypeVar("T")
U = tp.TypeVar("U")

ConvertResponseValues: tp.TypeAlias = bool | dict[str, object] | T | NotSpecifiedMeta
ConvertResponseGenerator: tp.TypeAlias = tp.Generator[
    tp.Optional[ConvertResponseValues[T] | tp.Generator], T, None
]

ConvertResponse: tp.TypeAlias = tp.Optional[ConvertResponseValues[T] | ConvertResponseGenerator[T]]

ConvertDefinitionNoValue: tp.TypeAlias = tp.Callable[[], ConvertResponse[T]]
ConvertDefinitionValue: tp.TypeAlias = tp.Callable[[object], ConvertResponse[T]]
ConvertDefinitionValueAndType: tp.TypeAlias = tp.Callable[[object, "Type"], ConvertResponse[T]]
# Also allowed is
# - (Any, Type, /, meta1, meta2, ...)
# - (Any, /, meta1, meta2, ...)
# But python typing is restrictive and you can't express that

ConvertDefinition: tp.TypeAlias = tp.Callable[..., ConvertResponse[T]]
ConvertFunction: tp.TypeAlias = tp.Callable[["CreateArgs"], T]


@define
class Annotation:
    @property
    def merge_meta(self) -> bool:
        return False


@tp.runtime_checkable
class Ann(tp.Protocol[T]):
    def adjusted_meta(self, meta: Meta, typ: "Type[T]") -> Meta:
        ...

    def adjusted_creator(
        self, creator: ConvertFunction[T] | None, register: "CreateRegister", typ: "Type[T]"
    ) -> ConvertFunction[T] | None:
        ...


@tp.runtime_checkable
class AdjustableMeta(tp.Protocol[T]):
    def adjusted_meta(self, meta: Meta, typ: "Type[T]") -> Meta:
        ...


class Type(tp.Generic[T]):
    original: object
    want: object
    ann: Ann | None
    origin: object
    checkable: type

    @classmethod
    def create(cls, original: object, *, _made: dict[object, "Type"] | None = None) -> "Type":
        if isinstance(original, Type):
            return original

        if _made is None:
            _made = {}
        return Type(original, _made=_made)

    @define
    class _Field:
        name: str
        type: type

    @define
    class Field:
        name: str
        type: "Type"

    def __init__(self, original: object, *, _made: dict[object, "Type"] | None = None):
        self._made = _made
        self.original = original
        self.optional, self.want, self.checkable = extract_type(self.original)

        ann: Ann[T] | None = None
        metadata: tuple[object] | None = getattr(self.want, "__metadata__", None)
        ann_value: object | None = None

        if metadata is not None and metadata:
            ann_value = metadata[0]

            origin = getattr(self.want, "__origin__", None)
            if origin is not None:
                self.want = origin

        if ann_value is not None and (
            isinstance(ann_value, (Ann, Annotation)) or callable(ann_value)
        ):
            from .annotations import AnnBase

            if isinstance(ann_value, Ann):
                ann = ann_value
            elif isinstance(ann_value, (Annotation, AdjustableMeta)):
                ann = AnnBase[T](ann_value)
            elif callable(ann_value):
                ann = AnnBase[T](creator=ann_value)

        self.ann = ann
        self.ann_value = ann_value
        self.origin = tp.get_origin(self.want)
        self.is_annotated = self.ann_value is not None

        self.fields_from: object = self.want
        self.typevar_map: dict[tp.TypeVar, type] = {}
        self.typevars: list[tp.TypeVar] = []

        for base in getattr(self.origin, "__orig_bases__", ()):
            self.typevars.extend(tp.get_args(base))

        for tv, ag in zip(self.typevars, tp.get_args(self.want)):
            self.typevar_map[tv] = ag

        if (
            not isinstance(self.want, type)
            or (not attrs_has(self.want) and not dataclasses.is_dataclass(self.want))
            and self.origin
        ):
            self.fields_from = self.origin

        self.fields_getter: tp.Callable[..., tp.Sequence[Type._Field]] | None = None

        if isinstance(self.fields_from, type) and attrs_has(self.fields_from):
            self.fields_getter = tp.cast(tp.Callable[..., tp.Sequence[Type._Field]], attrs.fields)
        elif dataclasses.is_dataclass(self.fields_from):
            self.fields_getter = tp.cast(
                tp.Callable[..., tp.Sequence[Type._Field]], dataclasses.fields
            )

        self.has_fields = self.fields_getter is not None

    def without_annotation(self) -> "Type[T]":
        typ = self.want
        if self.optional:
            typ = tp.Optional[self.want]
        return Type(typ)

    @property
    def fields(self) -> list[Field]:
        if self.fields_getter is None:
            return []

        fields: list[Type.Field] = []
        for field in self.fields_getter(self.fields_from):
            field_type = field.type
            if isinstance(field_type, tp.TypeVar):
                field_type = self.typevar_map.get(field.type, object)

            if self._made is not None:
                if field_type not in self._made:
                    self._made[field_type] = Type.create(field_type, _made=self._made)
                as_Type = self._made[field_type]
            else:
                as_Type = Type.create(field_type)

            fields.append(Type.Field(name=field.name, type=as_Type))

        return fields

    def __hash__(self) -> int:
        return hash(self.original)

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, Type):
            return False

        return self.original == o.original

    def __repr__(self) -> str:
        return repr(self.original)

    @property
    def processable(self) -> bool:
        return self.is_annotated or self.has_fields

    def is_type_for(self, instance: object) -> tp.TypeGuard[T]:
        return isinstance(instance, self.checkable)

    def is_equivalent_type_for(self, value: object) -> tp.TypeGuard[T]:
        if self.is_type_for(value):
            return True
        return issubclass(Type.create(type(value)).checkable, self.checkable)

    def resolve_types(self, *, _resolved: set["Type"] | None = None):
        if _resolved is None:
            _resolved = set()

        if self in _resolved:
            return
        _resolved.add(self)

        if isinstance(self.original, type):
            resolve_types(self.original)
        if isinstance(self.want, type):
            resolve_types(self.want)

        args = getattr(self.want, "__args__", None)
        if args:
            for arg in args:
                if isinstance(arg, type):
                    resolve_types(arg)

        for field in self.fields:
            field.type.resolve_types(_resolved=_resolved)

    def find_generic_subtype(self, *want: type) -> list[type]:
        result: list[type] = []
        for tv, wa in itertools.zip_longest(self.typevars, want):
            if wa is None:
                break
            if tv is None:
                raise ValueError(
                    f"The type has less typevars ({len(self.typevars)}) than wanted ({len(want)})"
                )

            typ = self.typevar_map[tv]
            if not issubclass(typ, want):
                raise ValueError(
                    f"The concrete type {typ} is not a subclass of what was asked for {wa}"
                )

            result.append(typ)

        return result

    def func_from(
        self, options: list[tuple[object, ConvertFunction[T]]]
    ) -> ConvertFunction[T] | None:
        for want, func in options:
            if want in (self.original, self.want):
                return func

        for want, func in options:
            if want is self.origin:
                return func

            check_against = want
            if isinstance(check_against, Type):
                check_against = check_against.checkable
            elif isinstance(check_against, type):
                check_against = Type.create(check_against).checkable

            if (
                isinstance(check_against, type)
                and isinstance(getattr(check_against, "_typ", None), type)
                and isinstance(getattr(self.checkable, "_typ", None), type)
                and issubclass(self.checkable, check_against)
            ):
                return func

        if not isinstance(self.origin, type):
            return None

        for want, func in options:
            if isinstance(want, type) and issubclass(self.origin, want):
                return func

        return None

    def fill(self, res: object) -> tp.Mapping[str, object]:
        if res is NotSpecified:
            res = {}

        if not isinstance(res, collections.abc.Mapping):
            raise ValueError(f"Can only fill mappings, got {type(res)}")

        if isinstance(res, dict) and self.has_fields:
            for field in self.fields:
                if field.type is not None and field.name not in res:
                    if field.type.processable:
                        res[field.name] = NotSpecified

        return res

    def convert(self, res: object, converter: cattrs.Converter) -> T:
        if self.optional and res is None:
            return tp.cast(T, None)

        if not callable(self.want):
            raise TypeError(f"Unsure how to instantiate a {type(self.want)}: {self.want}")

        res = self.fill(res)

        conv_obj: dict[str, object] = {}
        for field in self.fields:
            name = field.name

            if name not in res:
                continue

            val = res[name]
            if name.startswith("_"):
                name = name[1:]

            attribute = tp.cast(
                attrs.Attribute,
                Type._Field(name=field.name, type=tp.cast(type, field.type.original)),
            )
            conv_obj[name] = converter._structure_attribute(attribute, val)

        return self.want(**conv_obj)
