# coding: spec

from strcs.base import _ArgsExtractor
import strcs

from unittest import mock
import typing as tp
import inspect
import cattrs
import pytest

describe "NotSpecified":
    it "cannot be instantiated":
        with pytest.raises(Exception, match="Do not instantiate NotSpecified"):
            strcs.NotSpecified()

    it "has a reasonable repr":
        assert repr(strcs.NotSpecified) == "<NotSpecified>"

describe "_ArgsExtractor":
    it "no args to extract if no args in signature":

        def func():
            ...

        val = mock.Mock(name="val")
        extractor = _ArgsExtractor(
            inspect.signature(func), val, mock.Mock, strcs.Meta(), cattrs.Converter()
        )

        assert extractor.extract() == []

    it "can get value from the first positional argument":

        def func(value: tp.Any, /):
            ...

        val = mock.Mock(name="val")
        extractor = _ArgsExtractor(
            inspect.signature(func), val, mock.Mock, strcs.Meta(), cattrs.Converter()
        )

        assert extractor.extract() == [val]

    it "can get want from the second positional argument":

        def func(value: tp.Any, want: tp.Type, /):
            ...

        val = mock.Mock(name="val")
        extractor = _ArgsExtractor(
            inspect.signature(func), val, mock.Mock, strcs.Meta(), cattrs.Converter()
        )

        assert extractor.extract() == [val, mock.Mock]
