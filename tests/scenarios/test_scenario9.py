# coding: spec

from cattrs.errors import IterableValidationError
from textwrap import dedent
from attrs import define
import typing as tp
import traceback
import fnmatch
import pytest
import strcs


reg = strcs.CreateRegister()
creator = reg.make_decorator()


@define
class Sub:
    two: str


@define
class Other:
    one: int
    sub: Sub


@define
class Stuff:
    others: list[Other]


@creator(Other)
def create_other(value: object, /, multiply: int = 1) -> dict:
    if isinstance(value, str):
        raise ValueError("asdf")

    elif isinstance(value, dict):
        return value

    return {"one": value, "sub": {"three": 5}}


@creator(Sub)
def create_sub(value: object) -> tp.Generator[dict | None, Sub, None]:
    if isinstance(value, dict):
        res = yield value

        if res.two != value["two"]:
            raise TypeError("two was changed!")

    elif isinstance(value, int):
        raise ValueError("blah")

    return None


describe "Having reasonable error messages":

    it "has reasonable error messages":
        with pytest.raises(IterableValidationError) as e:
            reg.create(
                Stuff,
                {
                    "others": [
                        20,
                        "wat",
                        {"one": 3, "sub": {"two": lambda: 1}},
                        {"one": 3, "sub": 30},
                    ]
                },
            )

        message = dedent("".join(traceback.format_exception(e.value))).split("\n")
        want = (
            dedent(
                """
            + Exception Group Traceback (most recent call last):
            | cattrs.errors.IterableValidationError: While structuring list[tests.scenarios.test_scenario9.Other] (4 sub-exceptions)
            +-+---------------- 1 ----------------
              | Traceback (most recent call last):
              | TypeError: Sub.__init__() missing 1 required positional argument: 'two'
              |
              | During handling of the above exception, another exception occurred:
              |
              | Traceback (most recent call last):
              | strcs.errors.UnableToConvert:
              |
              |  |>> Failed to create: Sub.__init__() missing 1 required positional argument: 'two'
              |  |
              |  |   Trying to convert '{'three': 5}' into '<class 'tests.scenarios.test_scenario9.Sub'>'
              |  |
              |  |   Using creator '<function create_sub at *>' at */tests/scenarios/test_scenario9.py:44
              |
              | During handling of the above exception, another exception occurred:
              |
              | Traceback (most recent call last):
              | strcs.errors.UnableToConvert:
              |
              |  |>>
              |  |   Trying to convert '20' into '<class 'tests.scenarios.test_scenario9.Other'>'
              |  |
              |  |   Using creator '<function create_other at *>' at */tests/scenarios/test_scenario9.py:33
              +---------------- 2 ----------------
              | Traceback (most recent call last):
              |   File "*/tests/scenarios/test_scenario9.py", line 36, in create_other
              | ValueError: asdf
              |
              | During handling of the above exception, another exception occurred:
              |
              | Traceback (most recent call last):
              | strcs.errors.UnableToConvert:
              |
              |  |>> Failed to invoke creator: asdf
              |  |
              |  |   Trying to convert 'wat' into '<class 'tests.scenarios.test_scenario9.Other'>'
              |  |
              |  |   Using creator '<function create_other at *>' at */tests/scenarios/test_scenario9.py:33
              +---------------- 3 ----------------
              | Traceback (most recent call last):
              |   File "*/tests/scenarios/test_scenario9.py", line 50, in create_sub
              | TypeError: two was changed!
              |
              | During handling of the above exception, another exception occurred:
              |
              | Traceback (most recent call last):
              | strcs.errors.UnableToConvert:
              |
              |  |>> Something went wrong in the creator generator: two was changed!
              |  |
              |  |   Trying to convert '*' into '<class 'tests.scenarios.test_scenario9.Sub'>'
              |  |
              |  |   Using creator '<function create_sub at *>' at */tests/scenarios/test_scenario9.py:44
              |
              | During handling of the above exception, another exception occurred:
              |
              | Traceback (most recent call last):
              | strcs.errors.UnableToConvert:
              |
              |  |>>
              |  |   Trying to convert '*' into '<class 'tests.scenarios.test_scenario9.Other'>'
              |  |
              |  |   Using creator '<function create_other at *>' at */tests/scenarios/test_scenario9.py:33
              +---------------- 4 ----------------
              | Traceback (most recent call last):
              |   File "*/tests/scenarios/test_scenario9.py", line 53, in create_sub
              | ValueError: blah
              |
              | During handling of the above exception, another exception occurred:
              |
              | Traceback (most recent call last):
              | strcs.errors.UnableToConvert:
              |
              |  |>> Something went wrong in the creator generator: blah
              |  |
              |  |   Trying to convert '30' into '<class 'tests.scenarios.test_scenario9.Sub'>'
              |  |
              |  |   Using creator '<function create_sub at *>' at */tests/scenarios/test_scenario9.py:44
              |
              | During handling of the above exception, another exception occurred:
              |
              | Traceback (most recent call last):
              | strcs.errors.UnableToConvert:
              |
              |  |>>
              |  |   Trying to convert '*' into '<class 'tests.scenarios.test_scenario9.Other'>'
              |  |
              |  |   Using creator '<function create_other at *>' at */tests/scenarios/test_scenario9.py:33
              +------------------------------------
              """
            )
            .strip()
            .split("\n")
        )

        message = [line.strip() for line in message]
        want = [line.strip() for line in want]

        print("GOT >>" + "=" * 74)
        print()
        print("\n".join(message))
        print()
        print("WANT >>" + "-" * 73)
        print()
        print("\n".join(want))

        count = 1
        while want:
            line = want[0]
            if not message:
                assert False, f"Ran out of lines, stopped at [{count}] '{want[0]}'"

            if message[0] == line or fnmatch.fnmatch(message[0], line):
                count += 1
                want.pop(0)

            message.pop(0)

        if want:
            assert False, f"Didn't match all the lines, stopped at [{count}] '{want[0]}'"
