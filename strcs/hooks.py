"""
The heart of ``strcs`` is the hook that is created for cattrs. This hook handles
the requirement of passing around the meta object to deeply nested objects even
if there is an unbroken chain of ``strcs`` creators to reach that nested object.

This is done without recursion errors and with the ability to customize the result
for specific properties on a class.
"""

from typing import TYPE_CHECKING, TypeVar

import cattrs

from .annotations import (
    is_adjustable_creator,
    is_adjustable_meta,
)
from .decorator import ConvertDefinition, ConvertFunction, CreateArgs
from .disassemble import Type, TypeCache, fill, instantiate
from .meta import Meta
from .not_specified import NotSpecified

if TYPE_CHECKING:
    from .register import CreateRegister

T = TypeVar("T")
U = TypeVar("U")


def _object_check(typ: type) -> bool:
    """
    We need to be able to tell cattrs to passthrough anything with the type "object"

    This function is defined at the module level so that it can also be removed
    from cattrs when ``strcs`` is finished with it's processing.
    """
    return typ is object


def _passthrough(obj: object, typ: type) -> object:
    """
    We need to be able to tell cattrs to passthrough anything with the type "object"

    This function is defined at the module level so that it can also be removed
    from cattrs when ``strcs`` is finished with it's processing.
    """
    return obj


class CreateStructureHook:
    """
    This class knows how to register hooks to inject ``strcs`` logic into a
    cattrs Converter. Usage is via the ``structure`` classmethod which will
    do a structure with strcs logic and remove strcs hooks from the converter
    when done.
    """

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
            last_type=last_type,  # type: ignore[arg-type]
            skip_creator=skip_creator,  # type: ignore[arg-type]
            once_only_creator=creator,  # type: ignore[arg-type]
            type_cache=type_cache,
        )

        # Make sure cattrs doesn't complain about values with the type "object"
        converter.register_structure_hook_func(_object_check, _passthrough)

        # Insert the strcs conversion logic with a check function that lets us
        # also rely on cattrs logic, so that deeply nested values after a broken
        # chain of strcs conversions, still gets strcs logic
        converter.register_structure_hook_func(hooks.switch_check, hooks.convert)

        try:
            # Start by converting without cattrs logic
            ret = hooks.convert(value, typ)
        finally:
            # Ensure our strcs hooks are removed after they are used
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
            want = self.type_cache.disassemble(typ)

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

        if is_adjustable_meta(want.ann) or is_adjustable_creator(want.ann):
            if is_adjustable_meta(want.ann):
                meta = want.ann.adjusted_meta(meta, want, self.type_cache)
            if is_adjustable_creator(want.ann):
                creator = want.ann.adjusted_creator(  # type: ignore[assignment]
                    creator,  # type: ignore[arg-type]
                    self.register,
                    want,
                    self.type_cache,
                )
            if meta is not self.meta:
                return self.register.create(
                    self.type_cache.disassemble.typed(
                        type(want.extracted), want.without_annotation
                    ),
                    value,
                    meta=meta,
                    once_only_creator=creator,  # type: ignore[arg-type]
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
            return creator(
                CreateArgs(
                    value,
                    want,  # type: ignore[arg-type]
                    meta,
                    self.converter,
                    self.register,
                )
            )  # type: ignore[return-value]

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
        if hasattr(self.converter._structure_func.dispatch, "cache_clear"):
            self.converter._structure_func.dispatch.cache_clear()
        if isinstance(value, dict):
            value = fill(want, value)
        return self.converter.structure(
            value,
            want.original,  # type: ignore[arg-type]
        )
