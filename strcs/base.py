from .meta import Meta
from . import errors

import typing as tp
import inspect
import cattrs
import attrs

T = tp.TypeVar("T")


class NotSpecifiedMeta(type):
    def __repr__(self):
        return "<NotSpecified>"


class NotSpecified(metaclass=NotSpecifiedMeta):
    def __init__(self):
        raise Exception("Do not instantiate NotSpecified")


ConvertResponseValues: tp.TypeAlias = tp.Optional[bool | dict[str, tp.Any]]
ConvertResponseDirect: tp.TypeAlias = tp.Union[
    ConvertResponseValues, tp.Tuple[ConvertResponseValues, Meta]
]
ConvertResponseGenerator: tp.TypeAlias = tp.Generator[ConvertResponseValues | T, T, None]

ConvertResponse: tp.TypeAlias = ConvertResponseDirect | ConvertResponseGenerator[T] | T

ConvertDefinitionValue: tp.TypeAlias = tp.Callable[[tp.Any], ConvertResponse[T]]
ConvertDefinitionNoValue: tp.TypeAlias = tp.Callable[[], ConvertResponse[T]]
ConvertDefinitionValueAndType: tp.TypeAlias = tp.Callable[[tp.Any, tp.Type], ConvertResponse[T]]


class ConvertDefinitionValueAndData(tp.Protocol):
    def __call__(self, value: tp.Any, /, *values: tp.Any) -> ConvertResponse[T]:
        ...


class ConvertDefinitionValueAndTypeAndData(tp.Protocol):
    def __call__(self, value: tp.Any, want: tp.Type, /, *values: tp.Any) -> ConvertResponse[T]:
        ...


ConvertDefinition: tp.TypeAlias = tp.Union[
    ConvertDefinitionValue[T],
    ConvertDefinitionNoValue[T],
    ConvertDefinitionValueAndType[T],
    ConvertDefinitionValueAndData,
    ConvertDefinitionValueAndTypeAndData,
]
ConvertFunction: tp.TypeAlias = tp.Callable[[tp.Any, tp.Type, Meta, cattrs.Converter], T]


class CreateRegister:
    def __init__(self):
        self.register: dict[tp.Type[T], ConvertFunction[T]] = {}

    def __setitem__(self, typ: tp.Type[T], creator: ConvertFunction[T]) -> None:
        if not isinstance(typ, type):
            raise errors.CanOnlyRegisterTypes(got=typ)
        self.register[typ] = creator

    def __contains__(self, typ: tp.Type[T]) -> bool:
        return self.creator_for(typ) is not None

    def creator_for(self, typ: tp.Type[T]) -> tp.Optional[ConvertFunction[T]]:
        if not isinstance(typ, type):
            return None

        if typ in self.register:
            return self.register[typ]

        for t, func in self.register.items():
            if issubclass(typ, t):
                return func

        return None

    def create(self, typ: tp.Type[T], value: tp.Any = NotSpecified, meta: tp.Any = NotSpecified):
        if meta is NotSpecified:
            meta = Meta()

        converter = cattrs.Converter()

        cache: dict[tp.Type[T], ConvertFunction[T]] = {}

        def convert(value: tp.Any, want: tp.Type[T]) -> T:
            if want in cache:
                return cache[want](value, want, meta, converter)
            elif isinstance(value, want):
                return value
            else:
                return converter.structure_attrs_fromdict(value, want)

        def check_func(want: tp.Type[T]) -> bool:
            creator = self.creator_for(want)
            if creator is not None:
                cache[want] = creator
                return True
            return hasattr(want, "__attrs_attrs__")

        converter.register_structure_hook_func(check_func, convert)
        return converter.structure(value, typ)


class CreatorDecorator(tp.Generic[T]):
    func: ConvertDefinition[T]

    def __init__(self, register: CreateRegister, typ: tp.Type[T]):
        self.typ = typ
        self.register = register

    def __call__(self, func: ConvertDefinition[T]) -> ConvertDefinition[T]:
        self.func = func

        if hasattr(self.func, "side_effect"):
            # Hack to deal with mock objects
            self.signature = inspect.signature(self.func.side_effect)  # type: ignore
        else:
            self.signature = inspect.signature(self.func)

        self.register[self.typ] = self.wrapped
        return func

    def wrapped(self, value: tp.Any, want: tp.Type, meta: Meta, converter: cattrs.Converter) -> T:
        res = self._invoke_func(value, want, meta, converter)

        def deal(res: ConvertResponse[T], value: tp.Any) -> T:
            if res is None:
                raise errors.UnableToConvert(
                    converting=type(value),
                    into=want,
                    reason="Converter didn't return a value to use",
                )
            elif isinstance(res, want) or issubclass(type(res), self.typ):
                return tp.cast(T, res)
            elif res is True:
                if value is NotSpecified and not issubclass(want, type(NotSpecified)):
                    raise errors.UnableToConvert(
                        converting=value,
                        into=want,
                        reason="Told to use NotSpecified as the final value",
                    )
                return tp.cast(T, value)
            else:
                if res is NotSpecified:
                    res = {}
                if isinstance(res, dict):
                    for field in attrs.fields(want):
                        if (
                            field.type is not None
                            and field.type in self.register
                            and field.name not in res
                        ):
                            res[field.name] = NotSpecified
                return converter.structure_attrs_fromdict(tp.cast(dict, res), want)

        return deal(res, value)

    def _invoke_func(
        self, value: tp.Any, want: tp.Type, meta: Meta, converter: cattrs.Converter
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
            raise NotImplementedError()


Creator: tp.TypeAlias = tp.Callable[[tp.Type[T]], CreatorDecorator[T]]
