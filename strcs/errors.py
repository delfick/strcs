from textwrap import dedent
from attrs import define
import typing as tp
import inspect


@define
class StructuresError(Exception):
    ...


@define
class NoCreatorFound(StructuresError):
    want: tp.Type
    available: list[tp.Type]


@define
class UnableToConvert(StructuresError):
    creator: tp.Callable
    converting: tp.Type
    into: tp.Type
    reason: str
    error: None | Exception = None

    def __str__(self) -> str:
        return (
            "\n\n |>> "
            + (
                self.reason
                if self.error is None or not isinstance(self.error, UnableToConvert)
                else ""
            )
            + (
                "\n"
                if self.error is None or isinstance(self.error, UnableToConvert)
                else f": {self.error}\n | \n"
            )
            + "\n".join(
                f" |   {line}"
                for line in dedent(
                    f"""
        Trying to convert '{self.converting}' into '{self.into}'

        Using creator '{self.creator}'{self.creator_location}
        """
                )
                .strip()
                .split("\n")
            )
        )

    @property
    def creator_location(self) -> str:
        try:
            source_file = inspect.getsourcefile(self.creator)
        except:
            source_file = None

        if source_file is None:
            return ""

        try:
            line_numbers = inspect.getsourcelines(self.creator)
        except:
            return f" at {source_file}"
        else:
            return f" at {source_file}:{line_numbers[1]}"


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
