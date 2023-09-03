import typing as tp

import cattrs

from .annotations import (
    AdjustableCreator,
    AdjustableMeta,
    MergedMetaAnnotation,
    MetaAnnotation,
)
from .decorator import ConvertDefinition, ConvertFunction
from .disassemble.base import Type, TypeCache
from .hooks import CreateStructureHook
from .meta import Meta
from .not_specified import NotSpecified

T = tp.TypeVar("T")


class Registerer(tp.Protocol[T]):
    def __call__(self, func: ConvertDefinition[T] | None = None) -> ConvertDefinition[T]:
        ...


class Creator(tp.Protocol[T]):
    register: "CreateRegister"

    def __call__(self, typ: object, assume_unchanged_converted=True) -> Registerer[T]:
        ...


class CreateRegister:
    def __init__(
        self,
        *,
        register: dict[Type, ConvertFunction[T]] | None = None,
        last_meta: Meta | None = None,
        last_type: Type[T] | None = None,
        type_cache: TypeCache | None = None,
        skip_creator: ConvertDefinition[T] | None = None,
        auto_resolve_string_annotations: bool = True,
    ):
        if register is None:
            register = {}
        if type_cache is None:
            type_cache = TypeCache()

        self.register = register
        self.last_meta = last_meta
        self.last_type = last_type
        self.type_cache = type_cache
        self.skip_creator = skip_creator
        self.auto_resolve_string_annotations = auto_resolve_string_annotations

    def meta(
        self,
        data: dict[str, object] | None = None,
        converter: cattrs.Converter | None = None,
    ) -> Meta:
        return Meta(data, converter)

    def clone(
        self, last_meta: Meta, last_type: Type[T], skip_creator: ConvertDefinition[T]
    ) -> "CreateRegister":
        return type(self)(
            register=self.register,
            last_meta=last_meta,
            last_type=last_type,
            skip_creator=skip_creator,
            auto_resolve_string_annotations=self.auto_resolve_string_annotations,
        )

    def __setitem__(self, specification: type[T] | Type[T], creator: ConvertFunction[T]) -> None:
        self.register[Type.create(specification, cache=self.type_cache)] = creator

    def __contains__(self, typ: type | Type[T]) -> bool:
        if not isinstance(typ, (type, Type)):
            raise ValueError("Can only check against types or Type instances")

        return (
            Type.create(typ, expect=object, cache=self.type_cache).func_from(
                list(self.register.items())
            )
            is not None
        )

    def make_decorator(self) -> Creator:
        from .decorator import WrappedCreator

        register = self

        class Decorator(tp.Generic[T]):
            typ: Type[T]
            func: ConvertDefinition[T]
            wrapped: WrappedCreator[T]

            register: tp.ClassVar[CreateRegister]

            def __init__(self, typ: object, assume_unchanged_converted=True):
                self.original = typ
                self.assume_unchanged_converted = assume_unchanged_converted

            def __call__(
                self, func: ConvertDefinition[T] | None = None
            ) -> ConvertDefinition[T] | None:

                if not isinstance(self.original, Type):
                    typ: Type[T] = Type.create(self.original, cache=register.type_cache)
                else:
                    typ = self.original

                self.wrapped = WrappedCreator[T](
                    typ,
                    func,
                    type_cache=register.type_cache,
                    assume_unchanged_converted=self.assume_unchanged_converted,
                )
                self.typ = typ
                self.func = self.wrapped.func

                register[typ] = self.wrapped
                return func

        Decorator.register = register
        return Decorator

    def create(
        self,
        typ: type[T] | Type[T],
        value: object = NotSpecified,
        meta: Meta | None = None,
        once_only_creator: ConvertFunction[T] | None = None,
    ) -> T:
        if isinstance(typ, Type):
            want = typ
        else:
            want = Type.create(typ, cache=self.type_cache)

        return CreateStructureHook.structure(
            register=self,
            typ=want,
            meta=meta,
            value=value,
            creator=once_only_creator,
            last_meta=self.last_meta,
            last_type=self.last_type,
            type_cache=self.type_cache,
            skip_creator=self.skip_creator,
        )

    def create_annotated(
        self,
        typ: type[T] | Type[T],
        ann: MetaAnnotation
        | MergedMetaAnnotation
        | AdjustableMeta
        | AdjustableCreator
        | ConvertFunction[T],
        value: object = NotSpecified,
        meta: Meta | None = None,
        once_only_creator: ConvertFunction[T] | None = None,
    ) -> T:
        if isinstance(typ, Type):
            want = typ
        else:
            want = Type.create(tp.Annotated[typ, ann], cache=self.type_cache)

        return CreateStructureHook.structure(
            register=self,
            typ=want,
            meta=meta,
            value=value,
            creator=once_only_creator,
            last_meta=self.last_meta,
            last_type=self.last_type,
            type_cache=self.type_cache,
            skip_creator=self.skip_creator,
        )
