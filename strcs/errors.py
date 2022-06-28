from attrs import define
import typing as tp


@define
class StructuresError(Exception):
    ...


@define
class NoCreatorFound(StructuresError):
    want: tp.Type
    available: list[tp.Type]


@define
class UnableToConvert(StructuresError):
    converting: tp.Type
    into: tp.Type
    reason: str


@define
class NoDataByTypeName(StructuresError):
    want: tp.Type
    patterns: list[str]
    available: dict[str, tp.Type]


@define
class RequiredParam(StructuresError):
    why: str
    need: str
    have: list[str]


@define
class MultipleNamesForType(StructuresError):
    want: tp.Type
    found: list[str]


@define
class CanOnlyRegisterTypes(StructuresError):
    got: tp.Any


@define
class FoundWithWrongType(StructuresError):
    want: tp.Type
    patterns: list[str]


@define
class FailedToConvertIterable(StructuresError):
    message: str
    exceptions: list[Exception]
