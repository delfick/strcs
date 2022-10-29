from cattrs.errors import IterableValidationError
from textwrap import dedent
from attrs import define
import typing as tp
import traceback
import inspect


@define
class StructuresError(Exception):
    ...


@define
class NoCreatorFound(StructuresError):
    want: type
    available: list[type]


@define
class UnableToConvert(StructuresError):
    creator: tp.Callable
    converting: object
    into: type
    reason: str
    error: None | Exception = None

    def __str__(self) -> str:
        if isinstance(self.error, IterableValidationError):
            error_string = (
                "\n"
                + "\n".join(
                    f"  || {line}"
                    for line in "".join(traceback.format_exception(self.error)).split("\n")
                )
                + "\n | \n"
            )
        elif self.error is None or isinstance(self.error, UnableToConvert):
            error_string = "\n"
        else:
            error_string = f": {self.error}\n | \n"

        return (
            "\n\n |>> "
            + (
                self.reason
                if self.error is None or not isinstance(self.error, UnableToConvert)
                else ""
            )
            + error_string
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
    want: type
    patterns: list[str]
    available: dict[str, type]


@define
class RequiredParam(StructuresError):
    why: str
    need: str
    have: list[str]


@define
class MultipleNamesForType(StructuresError):
    want: type
    found: list[str]


@define
class CanOnlyRegisterTypes(StructuresError):
    got: object


@define
class FoundWithWrongType(StructuresError):
    want: type
    patterns: list[str]
