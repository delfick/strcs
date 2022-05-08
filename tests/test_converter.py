# coding: spec

# The @no_type_checks are because of https://github.com/python-attrs/cattrs/issues/111

import strcs

from cattr import Converter
import typing as tp
import pytest
import cattrs


@pytest.fixture()
def converter() -> Converter:
    return strcs.converter


describe "convert_str_list_str":

    @tp.no_type_check
    it "can convert a string", converter: Converter:
        assert converter.structure("hello", tp.Union[str, list[str]]) == "hello"

    @tp.no_type_check
    it "can convert a list of string", converter: Converter:
        assert converter.structure(["hello", "there"], tp.Union[str, list[str]]) == [
            "hello",
            "there",
        ]

    @tp.no_type_check
    it "can complain otherwise", converter: Converter:
        bad = [
            0,
            1,
            True,
            False,
            {},
            {"a": 1},
            set(),
            {1, 2},
            type("Kls", (), {}),
            type("instancer", (), {})(),
            lambda: 1,
        ]
        for thing in bad:
            with pytest.raises(Exception):
                converter.structure(thing, tp.Union[str, list[str]])

    it "is still necessary":
        with pytest.raises(Exception):
            cattrs.structure("hello", tp.Union[str, list[str]])
        with pytest.raises(Exception):
            cattrs.structure(["hello", "there"], tp.Union[str, list[str]])
