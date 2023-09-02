import typing as tp

import cattrs

from .annotations import Ann
from .decorator import ConvertDefinition, ConvertFunction, CreateArgs
from .disassemble.base import Type, TypeCache
from .disassemble.creation import fill, instantiate
from .meta import Meta
from .not_specified import NotSpecified

if tp.TYPE_CHECKING:
    from .register import CreateRegister

T = tp.TypeVar("T")
U = tp.TypeVar("U")


def _object_check(typ: type) -> bool:
    return typ is object


def _passthrough(obj: object, typ: type) -> object:
    return obj


class CreateStructureHook:
    @classmethod
    def structure(
        kls,
        *,
        register: "CreateRegister",
        typ: Type[T],
        type_cache: TypeCache,
        value: object = NotSpecified,
        meta: Meta | None = None,
        creator: ConvertFunction[T] | None = None,
        last_meta: Meta | None = None,
        last_type: Type[T] | None = None,
        skip_creator: ConvertDefinition[T] | None = None,
    ) -> T:
        if register.auto_resolve_string_annotations:
            typ.resolve_types()

        if meta is None:
            if last_meta is not None:
                meta = last_meta.clone()
            else:
                meta = register.meta()

        converter = meta.converter
        hooks = kls(
            register=register,
            converter=converter,
            meta=meta,
            last_meta=last_meta,
            last_type=last_type,
            skip_creator=skip_creator,
            once_only_creator=creator,
            type_cache=type_cache,
        )

        converter.register_structure_hook_func(_object_check, _passthrough)
        converter.register_structure_hook_func(hooks.switch_check, hooks.convert)

        try:
            ret = hooks.convert(value, typ)
        finally:
            converter._structure_func._function_dispatch._handler_pairs.remove(
                (hooks.switch_check, hooks.convert, False)
            )
            converter._structure_func._function_dispatch._handler_pairs.remove(
                (_object_check, _passthrough, False)
            )

        return ret

    def __init__(
        self,
        register: "CreateRegister",
        converter: cattrs.Converter,
        meta: Meta,
        *,
        type_cache: TypeCache,
        once_only_creator: ConvertFunction[T] | None = None,
        last_meta: Meta | None = None,
        last_type: Type[T] | None = None,
        skip_creator: ConvertDefinition[T] | None = None,
    ):
        self.meta = meta
        self.register = register
        self.do_check = True
        self.last_meta = last_meta
        self.last_type = last_type
        self.converter = converter
        self.type_cache = type_cache
        self.skip_creator = skip_creator
        self.once_only_creator = once_only_creator

    def convert(self, value: object, typ: type[T] | Type[T]) -> T:
        if isinstance(typ, Type):
            want = typ
        else:
            want = Type.create(typ, cache=self.type_cache)

        normal_creator = want.func_from(list(self.register.register.items()))

        if not bool(
            want.is_annotated or want.has_fields or self.once_only_creator or normal_creator
        ):
            return self.bypass(value, want)

        meta = self.meta
        creator = self.once_only_creator
        self.once_only_creator = None

        if normal_creator and creator is None:
            creator = normal_creator

        if isinstance(want.ann, Ann):
            meta = want.ann.adjusted_meta(meta, want, self.type_cache)
            creator = want.ann.adjusted_creator(creator, self.register, want, self.type_cache)
            if meta is not self.meta:
                return self.register.create(
                    Type.create(
                        want.without_annotation,
                        expect=type(want.extracted),
                        cache=self.type_cache,
                    ),
                    value,
                    meta=meta,
                    once_only_creator=creator,
                )

        if (
            # we have a creator
            creator is not None
            # and it's not skip_creator
            and creator is not self.skip_creator
            # and the creator isn't wrapping skip_creator
            and (
                self.skip_creator is None
                or getattr(creator, "func", None) not in (None, self.skip_creator)
            )
        ):
            return creator(CreateArgs(value, want, meta, self.converter, self.register))

        if want.is_type_for(value):
            return value
        else:
            return instantiate(want, value, self.converter)

    def switch_check(self, want: type) -> bool:
        ret = self.do_check
        self.do_check = True
        return ret

    def bypass(self, value: object, want: Type[T]) -> T:
        self.do_check = False
        self.converter._structure_func.dispatch.cache_clear()
        if isinstance(value, dict):
            value = fill(want, value)
        return self.converter.structure(value, tp.cast(type, want.original))
