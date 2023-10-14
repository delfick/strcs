"""
The register is how the developer can associate creator functions with
specific types.
"""
import typing as tp

import cattrs

from .annotations import (
    AdjustableCreator,
    AdjustableMeta,
    MergedMetaAnnotation,
    MetaAnnotation,
)
from .decorator import ConvertDefinition, ConvertFunction
from .disassemble import Type, TypeCache
from .hooks import CreateStructureHook
from .meta import Meta
from .not_specified import NotSpecified

T = tp.TypeVar("T")


class Registerer(tp.Protocol[T]):
    """
    Protocol representing an object that can decorate a ConvertDefinition for
    adding it to the register.

    It should return what it was given without changing it.
    """

    def __call__(self, func: ConvertDefinition[T] | None = None) -> ConvertDefinition[T] | None:
        ...


class Creator(tp.Protocol[T]):
    """
    Protocol representing an object that when called will returned a Registerer.
    """

    register: "CreateRegister"

    def __call__(self, typ: object, *, assume_unchanged_converted=True) -> Registerer[T]:
        ...


class CreateRegister:
    """
    The register is a central object that holds knowledge of how to transform data
    into different types. It is used to get a decorator that is used to add those
    :ref:`creators <features_creators>` and also used to then do a conversion:

    Usage looks like:

    .. code-block:: python

        import strcs

        reg = strcs.CreateRegister()
        creator = reg.make_decorator()

        # Then the creator may be used as a decorator to add knowledge about custom
        # transformations

        # Then objects may be created
        instance = reg.create(MyKls, some_data)
    """

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
        self.disassemble = type_cache.disassemble
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
        self.register[self.type_cache.disassemble(specification)] = creator

    def __contains__(self, typ: type | Type[T]) -> bool:
        if not isinstance(typ, (type, Type)):
            raise ValueError("Can only check against types or Type instances")

        return self.type_cache.disassemble(typ).func_from(list(self.register.items())) is not None

    def make_decorator(self) -> Creator:
        """
        Return an object that can be used to register Creators:

        .. code-block:: python

            import attrs
            import strcs

            reg = strcs.CreateRegister()
            creator = reg.make_decorator()


            @attrs.define
            class Thing:
                one: int


            @creator(Thing)
            def make_thing(value: object, /) -> strcs.ConvertResponse[Thing]:
                ...

            thing = reg.create(Thing, ...)

        The decorator is instantiated with the object the creator should be
        making. As well as optional a boolean called ``assume_unchanged_converted``
        which defaults to True.

        When ``assume_unchanged_converted`` is True then the creator is not
        called if the value is already the desired type. If it is False then
        it will always be called.
        """
        from .decorator import WrappedCreator

        register = self

        class Decorator(tp.Generic[T]):
            typ: Type[T]
            func: ConvertDefinition[T]
            wrapped: WrappedCreator[T]

            register: tp.ClassVar[CreateRegister]

            def __init__(self, typ: object, *, assume_unchanged_converted: bool = True):
                self.original = typ
                self.assume_unchanged_converted = assume_unchanged_converted

            def __call__(
                self, func: ConvertDefinition[T] | None = None
            ) -> ConvertDefinition[T] | None:

                if not isinstance(self.original, Type):
                    typ = register.type_cache.disassemble(self.original)
                else:
                    typ = self.original

                self.wrapped = WrappedCreator[T](
                    tp.cast(Type[T], typ),
                    func,
                    type_cache=register.type_cache,
                    assume_unchanged_converted=self.assume_unchanged_converted,
                )
                self.typ = tp.cast(Type[T], typ)
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
        """
        Create an instance of the specified type by transforming the provided
        value.

        If no ``meta`` is provided, then an empty meta is created.

        If ``once_only_creator`` is provided then it will be used as the entry
        point for conversion.
        """
        if isinstance(typ, Type):
            want = typ
        else:
            want = self.type_cache.disassemble(typ)

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
        """
        This is the same as ``reg.create`` but the type will be wrapped with the
        provided annotation.
        """
        if isinstance(typ, Type):
            want = typ
        else:
            want = tp.cast(Type[T], self.type_cache.disassemble(tp.Annotated[typ, ann]))

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
