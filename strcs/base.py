from .meta import Meta
from . import errors

import typing as tp
import cattrs

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
            return cache[want](value, want, meta, converter)

        def check_func(want: tp.Type[T]) -> bool:
            creator = self.creator_for(want)
            if creator is not None:
                cache[want] = creator
                return True
            return False

        converter.register_structure_hook_func(check_func, convert)
        return converter.structure(value, typ)
