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

    it "can get arbitrary values from meta":

        class Other:
            pass

        o = Other()

        def func(value: tp.Any, want: tp.Type, /, other: Other, blah: int, stuff: str):
            ...

        val = mock.Mock(name="val")
        meta = strcs.Meta()
        meta["stuff"] = "one"
        meta["one"] = 12
        meta["two"] = "two"
        meta["o"] = o

        extractor = _ArgsExtractor(inspect.signature(func), val, Other, meta, cattrs.Converter())
        assert extractor.extract() == [val, Other, o, 12, "one"]

        def func(value: tp.Any, /, other: Other, blah: int, stuff: str):
            ...

        extractor = _ArgsExtractor(inspect.signature(func), val, Other, meta, cattrs.Converter())
        assert extractor.extract() == [val, o, 12, "one"]

        def func(other: Other, blah: int, stuff: str):
            ...

        extractor = _ArgsExtractor(inspect.signature(func), val, Other, meta, cattrs.Converter())
        assert extractor.extract() == [o, 12, "one"]

        def func(other: Other):
            ...

        extractor = _ArgsExtractor(inspect.signature(func), val, Other, meta, cattrs.Converter())
        assert extractor.extract() == [o]

    it "can get us the meta object":

        def func(meta):
            ...

        val = mock.Mock(name="val")
        meta = strcs.Meta()
        extractor = _ArgsExtractor(
            inspect.signature(func), val, mock.Mock, meta, cattrs.Converter()
        )

        assert extractor.extract() == [meta]

        def func(m: strcs.Meta):
            ...

        extractor = _ArgsExtractor(
            inspect.signature(func), val, mock.Mock, meta, cattrs.Converter()
        )

        assert extractor.extract() == [meta]

        def func(val, /, m: strcs.Meta):
            ...

        extractor = _ArgsExtractor(
            inspect.signature(func), val, mock.Mock, meta, cattrs.Converter()
        )

        assert extractor.extract() == [val, meta]
