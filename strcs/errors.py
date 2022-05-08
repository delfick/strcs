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
