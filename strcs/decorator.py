import collections.abc
import inspect
import typing as tp

import cattrs
from attrs import define

from . import errors
from .args_extractor import ArgsExtractor
from .meta import Meta
from .not_specified import NotSpecified, NotSpecifiedMeta
from .types import Type

if tp.TYPE_CHECKING:
    from .register import CreateRegister

T = tp.TypeVar("T")


@define
class CreateArgs(tp.Generic[T]):
    value: object
    want: Type[T]
    meta: Meta
    converter: cattrs.Converter
    register: "CreateRegister"


ConvertResponseValues: tp.TypeAlias = bool | dict[str, object] | T | NotSpecifiedMeta
ConvertResponseGenerator: tp.TypeAlias = tp.Generator[
    tp.Optional[ConvertResponseValues[T] | tp.Generator], T, None
]

ConvertResponse: tp.TypeAlias = tp.Optional[ConvertResponseValues[T] | ConvertResponseGenerator[T]]

ConvertDefinitionNoValue: tp.TypeAlias = tp.Callable[[], ConvertResponse[T]]
ConvertDefinitionValue: tp.TypeAlias = tp.Callable[[object], ConvertResponse[T]]
ConvertDefinitionValueAndType: tp.TypeAlias = tp.Callable[[object, Type], ConvertResponse[T]]
# Also allowed is
# - (Any, Type, /, meta1, meta2, ...)
# - (Any, /, meta1, meta2, ...)
# But python typing is restrictive and you can't express that

ConvertDefinition: tp.TypeAlias = tp.Callable[..., ConvertResponse[T]]
ConvertFunction: tp.TypeAlias = tp.Callable[[CreateArgs], T]


def take_or_make(value: object, typ: Type[T], /) -> ConvertResponse[T]:
    if typ.is_type_for(value):
        return value
    elif isinstance(value, (dict, NotSpecifiedMeta)):
        return value
    else:
        return None


class WrappedCreator(tp.Generic[T]):
    def __init__(self, wrapped: tp.Callable[[CreateArgs], T], func: ConvertDefinition[T]):
        self.func = func
        self.wrapped = wrapped

    def __call__(self, create_args: "CreateArgs") -> T:
        return self.wrapped(create_args)

    def __repr__(self):
        return f"<Wrapped {self.func}>"


class CreatorDecorator(tp.Generic[T]):
    func: ConvertDefinition[T]

    def __init__(
        self,
        register: "CreateRegister",
        typ: object,
        assume_unchanged_converted=True,
    ):
        if not isinstance(typ, Type):
            typ = Type.create(typ)
        self.typ = typ
        self.register = register
        self.assume_unchanged_converted = assume_unchanged_converted

    def __call__(self, func: ConvertDefinition[T] | None = None) -> ConvertDefinition[T]:
        wrapped, func = self.wrap(func)
        self.register[self.typ] = wrapped
        return func

    def wrap(
        self, func: ConvertDefinition[T] | None = None
    ) -> tuple[ConvertFunction[T], ConvertDefinition[T]]:
        if func is None:
            self.func = tp.cast(ConvertDefinition[T], take_or_make)
        else:
            self.func = func

        if hasattr(self.func, "side_effect"):
            # Hack to deal with mock objects
            self.signature = inspect.signature(self.func.side_effect)  # type: ignore
        else:
            self.signature = inspect.signature(self.func)

        wrapped = WrappedCreator[T](self.wrapped, self.func)
        return wrapped, self.func

    def wrapped(self, create_args: CreateArgs[T]) -> T:
        want = create_args.want
        meta = create_args.meta
        value = create_args.value
        register = create_args.register
        converter = create_args.converter

        if self.assume_unchanged_converted and want.is_type_for(value):
            return tp.cast(T, value)

        try:
            res = self._invoke_func(value, want, meta, converter, register)
        except Exception as error:
            raise errors.UnableToConvert(
                converting=value,
                into=want,
                reason="Failed to invoke creator",
                error=error,
                creator=self.func,
            )

        def deal(res: ConvertResponse[T], value: object) -> T:
            if inspect.isgenerator(res):
                try:
                    return self._process_generator(res, value, deal)
                except errors.UnableToConvert:
                    raise
                except Exception as error:
                    raise errors.UnableToConvert(
                        converting=value,
                        into=want,
                        reason="Something went wrong in the creator generator",
                        error=error,
                        creator=self.func,
                    )
            elif res is None:
                raise errors.UnableToConvert(
                    converting=type(value),
                    into=want,
                    reason="Converter didn't return a value to use",
                    creator=self.func,
                )
            elif want.is_equivalent_type_for(res):
                return res
            elif res is True:
                if value is NotSpecified and not want.checkable == type(NotSpecified):
                    raise errors.UnableToConvert(
                        converting=value,
                        into=want,
                        reason="Told to use NotSpecified as the final value",
                        creator=self.func,
                    )
                return tp.cast(T, value)
            else:
                if not isinstance(res, collections.abc.Mapping) and issubclass(
                    want.checkable, Type.create(type(res)).checkable
                ):
                    raise errors.SupertypeNotValid(
                        want=want.checkable,
                        got=Type.create(type(res)).checkable,
                        reason="A Super type is not a valid value to convert",
                    )

                try:
                    return want.convert(res, converter)
                except Exception as error:
                    raise errors.UnableToConvert(
                        converting=value,
                        into=want,
                        reason="Failed to create",
                        error=error,
                        creator=self.func,
                    )

        return deal(res, value)

    def _process_generator(
        self,
        res: ConvertResponseGenerator[T],
        value: object,
        deal: tp.Callable[[ConvertResponse[T], object], T],
    ) -> T:
        try:
            made: ConvertResponse[T]

            try:
                made = deal(next(res), value)
            except StopIteration:
                made = None
            else:
                try:
                    made2 = res.send(made)
                    if made2 is True:
                        value = made
                    made = made2
                except StopIteration:
                    pass

            return deal(made, value)
        finally:
            res.close()

    def _invoke_func(
        self,
        value: object,
        want: Type[T],
        meta: Meta,
        converter: cattrs.Converter,
        register: "CreateRegister",
    ) -> ConvertResponse[T]:

        if len(self.signature.parameters) == 0:
            return tp.cast(ConvertDefinitionNoValue, self.func)()

        elif len(self.signature.parameters) == 1:
            return tp.cast(ConvertDefinitionValue, self.func)(value)

        elif len(self.signature.parameters) == 2 and all(
            v.kind is inspect.Parameter.POSITIONAL_ONLY for v in self.signature.parameters.values()
        ):
            return tp.cast(ConvertDefinitionValueAndType, self.func)(value, want)

        else:
            args = ArgsExtractor(
                signature=self.signature,
                value=value,
                want=want,
                meta=meta,
                converter=converter,
                register=register,
                creator=self.func,
            ).extract()
            return self.func(*args)
