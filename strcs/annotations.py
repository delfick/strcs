import typing as tp

import attrs
from attrs import define

from .decorator import (
    ConvertDefinition,
    ConvertFunction,
    ConvertResponse,
    CreatorDecorator,
)
from .disassemble import Type
from .meta import Meta

if tp.TYPE_CHECKING:
    from .register import CreateRegister

T = tp.TypeVar("T")


@define
class Annotation:
    @property
    def merge_meta(self) -> bool:
        return False


@tp.runtime_checkable
class Ann(tp.Protocol[T]):
    def adjusted_meta(self, meta: Meta, typ: Type[T]) -> Meta:
        ...

    def adjusted_creator(
        self, creator: ConvertFunction[T] | None, register: "CreateRegister", typ: Type[T]
    ) -> ConvertFunction[T] | None:
        ...


@tp.runtime_checkable
class AdjustableMeta(tp.Protocol[T]):
    def adjusted_meta(self, meta: Meta, typ: "Type[T]") -> Meta:
        ...


class AnnBase(tp.Generic[T]):
    _func: ConvertFunction[T] | None = None

    def __init__(
        self,
        meta: Annotation | AdjustableMeta[T] | None = None,
        creator: ConvertDefinition[T] | None = None,
    ):
        self.meta = meta
        self.creator = creator

    def adjusted_meta(self, meta: Meta, typ: Type[T]) -> Meta:
        if self.meta is None:
            return meta

        if isinstance(self.meta, AdjustableMeta):
            return self.meta.adjusted_meta(meta, typ)

        if self.meta.merge_meta and attrs.has(self.meta.__class__):
            clone = meta.clone()
            for field in attrs.fields(self.meta.__class__):  # type:ignore
                if not field.name.startswith("_"):
                    optional = Type.create(field.type).optional
                    val = getattr(self.meta, field.name)
                    if not optional or val is not None:
                        clone[field.name] = val
            return clone
        else:
            return meta.clone({"__call_defined_annotation__": self.meta})

    def adjusted_creator(
        self, creator: ConvertFunction[T] | None, register: "CreateRegister", typ: Type[T]
    ) -> ConvertFunction[T] | None:
        if self.creator is None:
            return creator

        wrapped, _ = CreatorDecorator[T](
            register, typ, assume_unchanged_converted=typ.has_fields
        ).wrap(self.creator)

        return wrapped


@define(frozen=True)
class FromMeta:
    pattern: str

    def adjusted_meta(self, meta: Meta, typ: "Type[T]") -> Meta:
        val: T = meta.retrieve_one(typ.checkable_as_type, self.pattern)
        return meta.clone(data_override={"retrieved": val})

    def adjusted_creator(
        self, creator: ConvertFunction | None, register: "CreateRegister", typ: "Type[T]"
    ) -> ConvertFunction[T] | None:
        def retrieve(value: object, /, _meta: Meta) -> ConvertResponse[T]:
            return tp.cast(T, _meta.retrieve_one(object, "retrieved"))

        a = AnnBase[T](creator=retrieve)
        return a.adjusted_creator(creator, register, typ)


@define
class MergedAnnotation(Annotation):
    @property
    def merge_meta(self) -> bool:
        return True
