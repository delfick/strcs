import collections
import typing as tp

import attrs
import cattrs
from attrs import define

from .disassemble import Disassembled, Field
from .hints import resolve_types
from .memoized_property import memoized_property
from .meta import Meta
from .not_specified import NotSpecified

if tp.TYPE_CHECKING:
    from .decorator import ConvertFunction
    from .register import CreateRegister


T = tp.TypeVar("T")
U = tp.TypeVar("U")


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
        self, creator: tp.Optional["ConvertFunction[T]"], register: "CreateRegister", typ: "Type[T]"
    ) -> tp.Optional["ConvertFunction[T]"]:
        ...


@tp.runtime_checkable
class AdjustableMeta(tp.Protocol[T]):
    def adjusted_meta(self, meta: Meta, typ: "Type[T]") -> Meta:
        ...


class Type(Disassembled[T]):
    @classmethod
    def create(
        cls,
        typ: object,
        *,
        expect: type[U] | None = None,
        _cache: collections.abc.MutableMapping[object, "Disassembled"] | None = None,
    ) -> "Type[U]":
        constructor = tp.cast(tp.Callable[..., Type[U]], super().create)
        return constructor(typ, _cache=_cache)

    def __repr__(self) -> str:
        return repr(self.original)

    @memoized_property
    def fields(self) -> list[Field]:
        res: list[Field] = []
        for field in super().fields:
            if field.type is None:
                res.append(field.with_replaced_type(field.type))
            else:
                res.append(field.with_replaced_type(self.create(field.type)))
        return res

    def resolve_types(self, *, _resolved: set["Type"] | None = None):
        if _resolved is None:
            _resolved = set()

        if self in _resolved:
            return
        _resolved.add(self)

        if isinstance(self.original, type):
            resolve_types(self.original)
        if isinstance(self.extracted, type):
            resolve_types(self.extracted)

        args = getattr(self.extracted, "__args__", None)
        if args:
            for arg in args:
                if isinstance(arg, type):
                    resolve_types(arg)

        for field in self.fields:
            field.type.resolve_types(_resolved=_resolved)

    def func_from(
        self, options: list[tuple["Type", "ConvertFunction[T]"]]
    ) -> tp.Optional["ConvertFunction[T]"]:
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
            for field in self.fields:
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
        for field in self.fields:
            name = field.name

            if name not in res:
                continue

            val = res[name]
            if name.startswith("_"):
                name = name[1:]

            attribute = tp.cast(
                attrs.Attribute,
                Field(name=field.name, type=tp.cast(type, field.type.original)),
            )
            conv_obj[name] = converter._structure_attribute(attribute, val)

        return self.extracted(**conv_obj)

    @memoized_property
    def ann(self) -> object | None:
        ann: Ann[T] | None = None
        if self.annotation is not None and (
            isinstance(self.annotation, (Ann, Annotation)) or callable(self.annotation)
        ):
            from .annotations import AnnBase

            if isinstance(self.annotation, Ann):
                ann = self.annotation
            elif isinstance(self.annotation, (Annotation, AdjustableMeta)):
                ann = AnnBase[T](self.annotation)
            elif callable(self.annotation):
                ann = AnnBase[T](creator=self.annotation)

        return ann
