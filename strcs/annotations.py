"""
Developers may target customization for specific fields by annotating their types
with objects that ``strcs`` knows how to use.

This is done by taking advantage of the ``typing.Annotated`` functionality that
has existed since Python 3.9

There are two interfaces that ``strcs`` will look for when determining if a
``typing.Annotation`` value may be used to customize creation.

.. autoprotocol:: strcs.AdjustableMeta

.. autoprotocol:: strcs.AdjustableCreator

``strcs`` will also recognise instances of ``strcs.MetaAnnotation`` and
``strcs.MergedMetaAnnotation`` and turn those into instances of ``strcs.Ann``,
which is a concrete implementation of both ``AdjustableMeta`` and ``AdjustableCreator``.
Callable objects will also be turned into a ``strcs.Ann`` by treating the callable
object as a creator override.
"""
import typing as tp

import attrs

from .decorator import (
    ConvertDefinition,
    ConvertFunction,
    ConvertResponse,
    WrappedCreator,
)
from .disassemble import Type, TypeCache
from .meta import Meta

if tp.TYPE_CHECKING:
    from .register import CreateRegister

T = tp.TypeVar("T")


@tp.runtime_checkable
class AdjustableMeta(tp.Protocol[T]):
    """
    An interface used to modify the meta object when creating a field.

    The hook is provided the original meta object, the type that needs to be created,
    and the current type cache.

    This hook must return the meta object to use. Modifications to the meta object
    must be made on a clone of the meta object.

    The new Meta will persist for any transformation that occurs below the field.
    """

    def adjusted_meta(self, meta: Meta, typ: Type[T], type_cache: TypeCache) -> Meta:
        ...


@tp.runtime_checkable
class AdjustableCreator(tp.Protocol[T]):
    """
    An interface used to modify the creator used when creating a field.

    The hook is provided the original creator function that would be used, the
    current ``strcs`` register, the type that needs to be created,
    and the current type cache.

    This hook must return either a creator function or None.

    If None is returned, ``strcs`` will fallback to the original creator that would
    be used.

    .. note:: The return of this is a ``strcs.ConvertFunction`` which is a normalised
       form of the creator functions that developers interact with. It is recommended to
       do the following to convert such a function into the ``strcs.ConvertFunction`` form:

       .. code-block:: python

           a = strcs.Ann[T](creator=my_function)
           return a.adjusted_creator(creator, register, typ, type_cache)
    """

    def adjusted_creator(
        self,
        creator: ConvertFunction[T] | None,
        register: "CreateRegister",
        typ: Type[T],
        type_cache: TypeCache,
    ) -> ConvertFunction[T] | None:
        ...


@attrs.define
class MetaAnnotation:
    """
    A class representing information that may be added into into the meta object
    used at creation time.

    When ``strcs`` sees this object in a ``typing.Annotation`` for the type of a
    field, it will create a ``strcs.Ann(meta=instance)`` and the ``adjusted_meta``
    hook will add a ``__call_defined_annotation__`` property to the meta object
    holding the instance so that it can be asked for in the creator as
    ``annotation``.

    Usage looks like:

    .. code-block:: python

        import attrs
        import typing as tp
        import strcs

        reg = strcs.CreateRegister()
        creator = reg.make_decorator()


        @attrs.define(frozen=True)
        class MyAnnotation(strcs.MetaAnnotation):
            one: int
            two: int


        @attrs.define
        class MyKls:
            key: tp.Annotated[str, MyAnnotation(one=1, two=2)]


        @creator(MyKls)
        def create_mykls(value: object, /, annotation: MyAnnotation) -> dict | None:
            if not isinstance(value, str):
                return None
            return {"key": f"{value}-{annotation.one}-{annotation.two}"}
    """


@attrs.define
class MergedMetaAnnotation:
    """
    A class representing information that may be merged into into the meta object
    used at creation time.

    When ``strcs`` sees this object in a ``typing.Annotation`` for the type of a
    field, it will create a ``strcs.Ann(meta=instance)`` and the ``adjusted_meta``
    hook will add all the fields on the instance onto the meta object, overriding
    any fields with the same key.

    Usage looks like:

    .. code-block:: python

        import attrs
        import typing as tp
        import strcs

        reg = strcs.CreateRegister()
        creator = reg.make_decorator()


        @attrs.define(frozen=True)
        class MyAnnotation(strcs.MergedMetaAnnotation):
            one: int
            two: int


        @attrs.define
        class MyKls:
            key: tp.Annotated[str, MyAnnotation(one=1, two=2)]



        @creator(MyKls)
        def create_mykls(value: object, /, one: int = 0, two: int = 0) -> dict | None:
            if not isinstance(value, str):
                return None
            return {"key": f"{value}-{one}-{two}"}

    Optional keys are not added to meta if they are not set:

    .. code-block:: python

        @attrs.define(frozen=True)
        class MyAnnotation(strcs.MergedMetaAnnotation):
            one: int | None = None
            two: int | None = None


        @creator(MyKls)
        def create_mykls(value: object, /, one: int = 0, two: int = 0) -> dict | None:
            if not isinstance(value, str):
                return None

            # one and two will be zero each instead of None when MyKls
            # is annotated with either of those not set respectively
            return {"key": f"{value}-{one}-{two}"}
    """


class Ann(tp.Generic[T]):
    """
    A concrete implementation of both ``strcs.AdjustedMeta`` and
    ``strcs.AdjustedCreator``.

    This object takes in a ``meta`` and a ``creator`` (both are optional) and
    will adjust the meta and/or creator based on those values.

    The creator object may be any ``strcs.ConvertDefinition`` callable and will
    be used as a creator override if provided.

    The meta object may be either an object satisfying ``strcs.AdjustableMeta``
    or an instance of ``strcs.MetaAnnotation`` or ``strcs.MergedMetaAnnotation``.

    .. autoclass:: strcs.MetaAnnotation

    .. autoclass:: strcs.MergedMetaAnnotation
    """

    _func: ConvertFunction[T] | None = None

    def __init__(
        self,
        meta: MetaAnnotation | MergedMetaAnnotation | AdjustableMeta[T] | None = None,
        creator: ConvertDefinition[T] | None = None,
    ):
        self.meta = meta
        self.creator = creator

    def adjusted_meta(self, meta: Meta, typ: Type[T], type_cache: TypeCache) -> Meta:
        if self.meta is None:
            return meta

        if isinstance(self.meta, AdjustableMeta):
            return self.meta.adjusted_meta(meta, typ, type_cache)

        if attrs.has(self.meta.__class__):
            if isinstance(self.meta, MergedMetaAnnotation):
                clone = meta.clone()
                for field in attrs.fields(self.meta.__class__):  # type:ignore
                    if not field.name.startswith("_"):
                        optional = type_cache.disassemble(field.type).optional
                        val = getattr(self.meta, field.name)
                        if not optional or val is not None:
                            clone[field.name] = val
                return clone
            elif isinstance(self.meta, MetaAnnotation):
                return meta.clone({"__call_defined_annotation__": self.meta})

        return meta

    def adjusted_creator(
        self,
        creator: ConvertFunction[T] | None,
        register: "CreateRegister",
        typ: Type[T],
        type_cache: TypeCache,
    ) -> ConvertFunction[T] | None:
        if self.creator is None:
            return creator

        return WrappedCreator[T](
            typ, self.creator, type_cache=type_cache, assume_unchanged_converted=typ.has_fields
        )


@attrs.define(frozen=True)
class FromMeta:
    """
    An implementation of both ``strcs.AdjustedMeta`` and ``strcs.AdjustedCreator``
    used to override a value with something found in the meta object.

    Usage looks like:

    .. code-block:: python

        import attrs
        import typing as tp
        import strcs

        reg = strcs.CreateRegister()
        creator = reg.make_decorator()


        class Magic:
            def incantation(self) -> str:
                return "abracadabra!"


        @attrs.define
        class Wizard:
            magic: tp.Annotated[Magic, strcs.FromMeta("magic")]


        wizard = reg.create(Wizard, meta=reg.meta({"magic": Magic()}))
        assert wizard.magic.incantation() == "abracadabra!"
    """

    pattern: str

    def adjusted_meta(self, meta: Meta, typ: "Type[T]", type_cache: TypeCache) -> Meta:
        val: T = meta.retrieve_one(typ.checkable_as_type, self.pattern, type_cache=type_cache)
        return meta.clone(data_override={"retrieved": val})

    def adjusted_creator(
        self,
        creator: ConvertFunction | None,
        register: "CreateRegister",
        typ: "Type[T]",
        type_cache: TypeCache,
    ) -> ConvertFunction[T] | None:
        def retrieve(value: object, /, _meta: Meta) -> ConvertResponse[T]:
            return tp.cast(T, _meta.retrieve_one(object, "retrieved", type_cache=type_cache))

        a = Ann[T](creator=retrieve)
        return a.adjusted_creator(creator, register, typ, type_cache)
