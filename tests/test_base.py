# coding: spec

from strcs.base import _ArgsExtractor
import strcs

from unittest import mock
import typing as tp
import inspect
import cattrs
import pytest


@pytest.fixture()
def meta() -> strcs.Meta:
    return strcs.Meta()


class IsRegister:
    def __init__(
        self,
        reg: strcs.CreateRegister,
        last_type: type,
        last_meta: strcs.Meta,
        skip_creator: strcs.ConvertDefinition,
    ):
        self.reg = reg
        self.got: None | object = None
        self.last_type = last_type
        self.last_meta = last_meta
        self.skip_creator = skip_creator

    def __eq__(self, other: object) -> bool:
        self.got = other
        return (
            isinstance(other, strcs.CreateRegister)
            and other.register is self.reg.register
            and other.last_type is self.last_type
            and other.last_meta is self.last_meta
            and other.skip_creator is self.skip_creator
        )

    def __repr__(self) -> str:
        if self.got is None:
            return "<IsRegister>"
        else:
            return repr(self.got)


describe "NotSpecified":
    it "cannot be instantiated":
        with pytest.raises(Exception, match="Do not instantiate NotSpecified"):
            strcs.NotSpecified()

    it "has a reasonable repr":
        assert repr(strcs.NotSpecified) == "<NotSpecified>"

describe "_ArgsExtractor":
    it "no args to extract if no args in signature", meta: strcs.Meta:

        def func():
            ...

        val = mock.Mock(name="val")
        extractor = _ArgsExtractor(
            signature=inspect.signature(func),
            value=val,
            want=mock.Mock,
            meta=meta,
            converter=cattrs.Converter(),
            register=strcs.CreateRegister(),
            creator=func,
        )

        assert extractor.extract() == []

    it "can get value from the first positional argument", meta: strcs.Meta:

        def func(value: object, /):
            ...

        val = mock.Mock(name="val")
        extractor = _ArgsExtractor(
            signature=inspect.signature(func),
            value=val,
            want=mock.Mock,
            meta=meta,
            converter=cattrs.Converter(),
            register=strcs.CreateRegister(),
            creator=func,
        )

        assert extractor.extract() == [val]

    it "can get want from the second positional argument", meta: strcs.Meta:

        def func(value: object, want: tp.Type, /):
            ...

        val = mock.Mock(name="val")
        extractor = _ArgsExtractor(
            signature=inspect.signature(func),
            value=val,
            want=mock.Mock,
            meta=meta,
            converter=cattrs.Converter(),
            register=strcs.CreateRegister(),
            creator=func,
        )

        assert extractor.extract() == [val, mock.Mock]

    it "can get arbitrary values from meta", meta: strcs.Meta:

        class Other:
            pass

        o = Other()

        def func(value: object, want: tp.Type, /, other: Other, blah: int, stuff: str):
            ...

        val = mock.Mock(name="val")
        meta["stuff"] = "one"
        meta["one"] = 12
        meta["two"] = "two"
        meta["o"] = o

        extractor = _ArgsExtractor(
            signature=inspect.signature(func),
            value=val,
            want=Other,
            meta=meta,
            converter=cattrs.Converter(),
            register=strcs.CreateRegister(),
            creator=func,
        )
        assert extractor.extract() == [val, Other, o, 12, "one"]

        def func2(value: object, /, other: Other, blah: int, stuff: str):
            ...

        extractor = _ArgsExtractor(
            signature=inspect.signature(func2),
            value=val,
            want=Other,
            meta=meta,
            converter=cattrs.Converter(),
            register=strcs.CreateRegister(),
            creator=func2,
        )
        assert extractor.extract() == [val, o, 12, "one"]

        def func3(other: Other, blah: int, stuff: str):
            ...

        extractor = _ArgsExtractor(
            signature=inspect.signature(func3),
            value=val,
            want=Other,
            meta=meta,
            converter=cattrs.Converter(),
            register=strcs.CreateRegister(),
            creator=func3,
        )
        assert extractor.extract() == [o, 12, "one"]

        def func4(other: Other):
            ...

        extractor = _ArgsExtractor(
            signature=inspect.signature(func4),
            value=val,
            want=Other,
            meta=meta,
            converter=cattrs.Converter(),
            register=strcs.CreateRegister(),
            creator=func4,
        )
        assert extractor.extract() == [o]

    it "can get us the meta object", meta: strcs.Meta:

        def func(_meta):
            ...

        val = mock.Mock(name="val")
        extractor = _ArgsExtractor(
            signature=inspect.signature(func),
            value=val,
            want=mock.Mock,
            meta=meta,
            converter=cattrs.Converter(),
            register=strcs.CreateRegister(),
            creator=func,
        )

        assert extractor.extract() == [meta]

        def func2(_meta: strcs.Meta):
            ...

        extractor = _ArgsExtractor(
            signature=inspect.signature(func2),
            value=val,
            want=mock.Mock,
            meta=meta,
            converter=cattrs.Converter(),
            register=strcs.CreateRegister(),
            creator=func2,
        )

        assert extractor.extract() == [meta]

        def func3(val, /, _meta: strcs.Meta):
            ...

        extractor = _ArgsExtractor(
            signature=inspect.signature(func3),
            value=val,
            want=mock.Mock,
            meta=meta,
            converter=cattrs.Converter(),
            register=strcs.CreateRegister(),
            creator=func3,
        )

        assert extractor.extract() == [val, meta]

    it "can get us based just off the name of the argument", meta: strcs.Meta:

        class Other:
            pass

        o = Other()

        def func(value: object, want: tp.Type, /, other, blah, stuff):
            ...

        val = mock.Mock(name="val")
        meta["stuff"] = "one"
        meta["blah"] = 12
        meta["other"] = o

        extractor = _ArgsExtractor(
            signature=inspect.signature(func),
            value=val,
            want=Other,
            meta=meta,
            converter=cattrs.Converter(),
            register=strcs.CreateRegister(),
            creator=func,
        )
        assert extractor.extract() == [val, Other, o, 12, "one"]

    it "can get us the converter object", meta: strcs.Meta:

        def func(_converter):
            ...

        val = mock.Mock(name="val")
        converter = cattrs.Converter()
        extractor = _ArgsExtractor(
            signature=inspect.signature(func),
            value=val,
            want=mock.Mock,
            meta=meta,
            converter=converter,
            register=strcs.CreateRegister(),
            creator=func,
        )

        assert extractor.extract() == [converter]

        def func2(_converter: cattrs.Converter):
            ...

        extractor = _ArgsExtractor(
            signature=inspect.signature(func2),
            value=val,
            want=mock.Mock,
            meta=meta,
            converter=converter,
            register=strcs.CreateRegister(),
            creator=func2,
        )

        assert extractor.extract() == [converter]

        def func3(val, /, _converter: cattrs.Converter):
            ...

        extractor = _ArgsExtractor(
            signature=inspect.signature(func3),
            value=val,
            want=mock.Mock,
            meta=meta,
            converter=converter,
            register=strcs.CreateRegister(),
            creator=func3,
        )

        assert extractor.extract() == [val, converter]

    it "can get us the register object", meta: strcs.Meta:

        reg = strcs.CreateRegister()

        def func(_register):
            ...

        val = mock.Mock(name="val")
        extractor = _ArgsExtractor(
            signature=inspect.signature(func),
            value=val,
            want=mock.Mock,
            meta=meta,
            converter=cattrs.Converter(),
            register=reg,
            creator=func,
        )

        assert extractor.extract() == [IsRegister(reg, mock.Mock, meta, func)]

        def func2(_register: strcs.CreateRegister):
            ...

        extractor = _ArgsExtractor(
            signature=inspect.signature(func2),
            value=val,
            want=mock.Mock,
            meta=meta,
            converter=cattrs.Converter(),
            register=reg,
            creator=func2,
        )

        assert extractor.extract() == [IsRegister(reg, mock.Mock, meta, func2)]

        def func3(val, /, _register: strcs.CreateRegister):
            ...

        extractor = _ArgsExtractor(
            signature=inspect.signature(func3),
            value=val,
            want=mock.Mock,
            meta=meta,
            converter=cattrs.Converter(),
            register=reg,
            creator=func3,
        )

        assert extractor.extract() == [val, IsRegister(reg, mock.Mock, meta, func3)]

    it "can get alternatives to the provided objects":
        val = mock.Mock(name="val")

        register1 = strcs.CreateRegister()
        register2 = strcs.CreateRegister()

        converter1 = cattrs.Converter()
        converter2 = cattrs.Converter()

        meta1 = strcs.Meta()
        meta2 = strcs.Meta()

        meta1["register"] = register2
        meta1["converter"] = converter2
        meta1["meta"] = meta2

        def func(_register, register, _meta, meta, _converter, converter):
            ...

        extractor = _ArgsExtractor(
            signature=inspect.signature(func),
            value=val,
            want=mock.Mock,
            meta=meta1,
            converter=converter1,
            register=register1,
            creator=func,
        )

        assert extractor.extract() == [
            IsRegister(register1, mock.Mock, meta1, func),
            register2,
            meta1,
            meta2,
            converter1,
            converter2,
        ]

        def func2(
            _register: strcs.CreateRegister,
            register: strcs.CreateRegister,
            _meta: strcs.Meta,
            meta: strcs.Meta,
            _converter: cattrs.Converter,
            converter: cattrs.Converter,
        ):
            ...

        extractor = _ArgsExtractor(
            signature=inspect.signature(func2),
            value=val,
            want=mock.Mock,
            meta=meta1,
            converter=converter1,
            register=register1,
            creator=func2,
        )

        assert extractor.extract() == [
            IsRegister(register1, mock.Mock, meta1, func2),
            register2,
            meta1,
            meta2,
            converter1,
            converter2,
        ]

        def func3(
            _register: str,
            register: strcs.CreateRegister,
            _meta: str,
            meta: strcs.Meta,
            _converter: str,
            converter: cattrs.Converter,
        ):
            ...

        extractor = _ArgsExtractor(
            signature=inspect.signature(func3),
            value=val,
            want=mock.Mock,
            meta=meta1,
            converter=converter1,
            register=register1,
            creator=func3,
        )

        with pytest.raises(strcs.errors.FoundWithWrongType) as exc_info:
            extractor.extract()

        assert exc_info.value.args == (str, ["_register"])

    it "complains if it can't find something", meta: strcs.Meta:

        def func(wat):
            ...

        extractor = _ArgsExtractor(
            signature=inspect.signature(func),
            value=mock.Mock(name="val"),
            want=mock.Mock,
            meta=meta,
            converter=cattrs.Converter(),
            register=strcs.CreateRegister(),
            creator=func,
        )

        with pytest.raises(strcs.errors.NoDataByTypeName) as exc_info:
            extractor.extract()

        assert exc_info.value.args[1] == ["wat"]

        def func2(wat: int):
            ...

        meta["one"] = 1
        meta["two"] = 2

        extractor = _ArgsExtractor(
            signature=inspect.signature(func2),
            value=mock.Mock(name="val"),
            want=mock.Mock,
            meta=meta,
            converter=cattrs.Converter(),
            register=strcs.CreateRegister(),
            creator=func2,
        )

        with pytest.raises(strcs.errors.MultipleNamesForType) as exc_info2:
            extractor.extract()

        assert exc_info2.value.args[1] == ["one", "two"]
