import inspect
import textwrap
import traceback
import typing as tp

import attrs
from cattrs.errors import IterableValidationError


@attrs.define
class StructuresError(Exception):
    ...


@attrs.define
class NoCreatorFound(StructuresError):
    want: object
    available: list[type]


@attrs.define
class UnableToConvert(StructuresError):
    creator: tp.Callable
    converting: object
    into: object
    reason: str
    error: Exception | None = None

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
                for line in textwrap.dedent(
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


@attrs.define
class NoDataByTypeName(StructuresError):
    want: object
    patterns: list[str]
    available: dict[str, type]


@attrs.define
class RequiredParam(StructuresError):
    why: str
    need: str
    have: list[str]


@attrs.define
class MultipleNamesForType(StructuresError):
    want: object
    found: list[str]


@attrs.define
class CanOnlyRegisterTypes(StructuresError):
    got: object


@attrs.define
class FoundWithWrongType(StructuresError):
    want: object
    patterns: list[str]


@attrs.define
class SupertypeNotValid(StructuresError):
    want: object
    got: object
    reason: str


@attrs.define
class NotValidType(StructuresError):
    pass
