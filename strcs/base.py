from .meta import Meta

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
ConvertFunction: tp.TypeAlias = tp.Callable[[tp.Any, Meta, cattrs.Converter], T]
