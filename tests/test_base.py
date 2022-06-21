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

    it "can get us based just off the name of the argument":

        class Other:
            pass

        o = Other()

        def func(value: tp.Any, want: tp.Type, /, other, blah, stuff):
            ...

        val = mock.Mock(name="val")
        meta = strcs.Meta()
        meta["stuff"] = "one"
        meta["blah"] = 12
        meta["other"] = o

        extractor = _ArgsExtractor(inspect.signature(func), val, Other, meta, cattrs.Converter())
        assert extractor.extract() == [val, Other, o, 12, "one"]

    it "can get us the converter object":

        def func(converter):
            ...

        val = mock.Mock(name="val")
        converter = cattrs.Converter()
        extractor = _ArgsExtractor(inspect.signature(func), val, mock.Mock, strcs.Meta(), converter)

        assert extractor.extract() == [converter]

        def func(c: cattrs.Converter):
            ...

        extractor = _ArgsExtractor(inspect.signature(func), val, mock.Mock, strcs.Meta(), converter)

        assert extractor.extract() == [converter]

        def func(val, /, c: cattrs.Converter):
            ...

        extractor = _ArgsExtractor(inspect.signature(func), val, mock.Mock, strcs.Meta(), converter)

        assert extractor.extract() == [val, converter]

    it "complains if it can't find something":

        def func(wat):
            ...

        extractor = _ArgsExtractor(
            inspect.signature(func),
            mock.Mock(name="val"),
            mock.Mock,
            strcs.Meta(),
            cattrs.Converter(),
        )

        with pytest.raises(strcs.errors.NoDataByTypeName) as exc_info:
            extractor.extract()

        assert exc_info.value.args[1] == ["wat"]

        def func(wat: int):
            ...

        meta = strcs.Meta()
        meta["one"] = 1
        meta["two"] = 2

        extractor = _ArgsExtractor(
            inspect.signature(func),
            mock.Mock(name="val"),
            mock.Mock,
            meta,
            cattrs.Converter(),
        )

        with pytest.raises(strcs.errors.MultipleNamesForType) as exc_info:
            extractor.extract()

        assert exc_info.value.args[1] == ["one", "two"]
