import collections
import typing as tp

import attrs
import cattrs
from attrs import define

from .disassemble import Disassembled, _Field
from .hints import resolve_types
from .meta import Meta
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
    @define
    class Field:
        name: str
        type: "Type"

    _ann: Ann[T] | None
    _fields: list[Field]
    _without_optional: "Type[T]"
    _without_annotation: "Type[T]"

    @classmethod
    def create(cls, original: object, *, _made: dict[object, "Type"] | None = None) -> "Type":
        if isinstance(original, Type):
            return original

        if _made is None:
            _made = {}
        return Type(original, _made=_made)

    def __init__(self, original: object, *, _made: dict[object, "Type"] | None = None):
        self._made = _made
        self.original = original
        self.disassembled = Disassembled.create(self.original)

        self.want = self.disassembled.extracted
        self.origin = tp.get_origin(self.want)

    def _make_type(self, typ: object) -> "Type":
        if self._made is None:
            return Type.create(typ)

        if typ not in self._made:
            self._made[typ] = Type.create(typ, _made=self._made)
        return self._made[typ]

    @property
    def optional(self) -> bool:
        return self.disassembled.optional

    @property
    def ann_value(self) -> object | None:
        return self.disassembled.annotation

    @property
    def ann(self) -> object | None:
        if not hasattr(self, "_ann"):
            ann: Ann[T] | None = None
            if self.ann_value is not None and (
                isinstance(self.ann_value, (Ann, Annotation)) or callable(self.ann_value)
            ):
                from .annotations import AnnBase

                if isinstance(self.ann_value, Ann):
                    ann = self.ann_value
                elif isinstance(self.ann_value, (Annotation, AdjustableMeta)):
                    ann = AnnBase[T](self.ann_value)
                elif callable(self.ann_value):
                    ann = AnnBase[T](creator=self.ann_value)
            self._ann = ann
        return self._ann

    @property
    def checkable(self) -> type:
        return self.disassembled.checkable

    @property
    def fields(self) -> list[Field]:
        if not hasattr(self, "_fields"):
            fields: list[Type.Field] = []
            for field in self.disassembled.fields:
                fields.append(Type.Field(name=field.name, type=self._make_type(field.type)))

            self._fields = fields
        return self._fields

    @property
    def without_annotation(self) -> "Type[T]":
        if not hasattr(self, "_without_annotation"):
            self._without_annotation = self._make_type(self.disassembled.without_annotation)
        return self._without_annotation

    def without_optional(self) -> "Type[T]":
        if not hasattr(self, "_without_optional"):
            self._without_optional = self._make_type(self.disassembled.without_optional)
        return self._without_optional

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
        return self.disassembled.is_annotated or self.disassembled.has_fields

    @property
    def has_fields(self) -> bool:
        return self.disassembled.has_fields

    def is_type_for(self, instance: object) -> tp.TypeGuard[T]:
        return self.disassembled.is_type_for(instance)

    def is_equivalent_type_for(self, value: object) -> tp.TypeGuard[T]:
        return self.disassembled.is_equivalent_type_for(
            value, lambda: self._make_type(type(value)).checkable
        )
        return issubclass(self._make_type(type(value)).checkable, self.checkable)

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
        return self.disassembled.find_generic_subtype(*want)

    def func_from(
        self, options: list[tuple["Type", ConvertFunction[T]]]
    ) -> ConvertFunction[T] | None:
        for want, func in options:
            if want in (self.original, self.want) or want == self:
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
                _Field(name=field.name, type=tp.cast(type, field.type.original)),
            )
            conv_obj[name] = converter._structure_attribute(attribute, val)

        return self.want(**conv_obj)
