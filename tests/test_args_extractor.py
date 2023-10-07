# coding: spec

import inspect
import typing as tp
from unittest import mock

import cattrs
import pytest

import strcs

T = tp.TypeVar("T")


@pytest.fixture()
def meta() -> strcs.Meta:
    return strcs.Meta()


@pytest.fixture(params=(True, False), ids=("with_cache", "without_cache"))
def type_cache(request: pytest.FixtureRequest) -> strcs.TypeCache:
    if request.param:
        return strcs.TypeCache()
    else:

        class Cache(strcs.TypeCache):
            def __setitem__(self, k: object, v: strcs.Type) -> None:
                return None

        return Cache()


@pytest.fixture()
def creg(type_cache: strcs.TypeCache) -> strcs.CreateRegister:
    return strcs.CreateRegister(type_cache=type_cache)


class IsRegister:
    def __init__(
        self,
        reg: strcs.CreateRegister,
        last_type: type[T],
        last_meta: strcs.Meta,
        skip_creator: strcs.ConvertDefinition,
    ):
        self.reg = reg
        self.got: object | None = None
        self.last_type = reg.disassemble(last_type)
        self.last_meta = last_meta
        self.skip_creator = skip_creator

    def __eq__(self, other: object) -> bool:
        self.got = other
        return (
            isinstance(other, strcs.CreateRegister)
            and other.register is self.reg.register
            and other.last_type == self.last_type
            and other.last_meta is self.last_meta
            and other.skip_creator is self.skip_creator
        )

    def __repr__(self) -> str:
        if self.got is None:
            return "<IsRegister>"
        else:
            return repr(self.got)


describe "ArgsExtractor":
    it "no args to extract if no args in signature", meta: strcs.Meta, creg: strcs.CreateRegister:

        def func() -> strcs.ConvertResponse[object]:
            ...

        val = mock.Mock(name="val")
        extractor = strcs.ArgsExtractor(
            signature=inspect.signature(func),
            value=val,
            want=creg.disassemble(object),
            meta=meta,
            converter=cattrs.Converter(),
            register=creg,
            creator=func,
        )

        assert extractor.extract() == []

    it "can get value from the first positional argument", meta: strcs.Meta, creg: strcs.CreateRegister:

        def func(value: object, /) -> strcs.ConvertResponse[object]:
            ...

        val = mock.Mock(name="val")
        extractor = strcs.ArgsExtractor(
            signature=inspect.signature(func),
            value=val,
            want=creg.disassemble(object),
            meta=meta,
            converter=cattrs.Converter(),
            register=creg,
            creator=func,
        )

        assert extractor.extract() == [val]

    it "can get want from the second positional argument", meta: strcs.Meta, creg: strcs.CreateRegister:

        def func(value: object, want: strcs.Type, /) -> strcs.ConvertResponse[object]:
            ...

        val = mock.Mock(name="val")
        extractor = strcs.ArgsExtractor(
            signature=inspect.signature(func),
            value=val,
            want=creg.disassemble(object),
            meta=meta,
            converter=cattrs.Converter(),
            register=creg,
            creator=func,
        )

        assert extractor.extract() == [
            val,
            creg.disassemble(object),
        ]

    it "can get arbitrary values from meta", meta: strcs.Meta, creg: strcs.CreateRegister:

        class Other:
            pass

        o = Other()

        def func(
            value: object, want: strcs.Type, /, other: Other, blah: int, stuff: str
        ) -> strcs.ConvertResponse[Other]:
            ...

        val = mock.Mock(name="val")
        meta["stuff"] = "one"
        meta["one"] = 12
        meta["two"] = "two"
        meta["o"] = o

        extractor = strcs.ArgsExtractor(
            signature=inspect.signature(func),
            value=val,
            want=creg.disassemble(Other),
            meta=meta,
            converter=cattrs.Converter(),
            register=creg,
            creator=func,
        )
        assert extractor.extract() == [
            val,
            creg.disassemble(Other),
            o,
            12,
            "one",
        ]

        def func2(
            value: object, /, other: Other, blah: int, stuff: str
        ) -> strcs.ConvertResponse[Other]:
            ...

        extractor = strcs.ArgsExtractor(
            signature=inspect.signature(func2),
            value=val,
            want=creg.disassemble(Other),
            meta=meta,
            converter=cattrs.Converter(),
            register=creg,
            creator=func2,
        )
        assert extractor.extract() == [val, o, 12, "one"]

        def func3(other: Other, blah: int, stuff: str) -> strcs.ConvertResponse[Other]:
            ...

        extractor = strcs.ArgsExtractor(
            signature=inspect.signature(func3),
            value=val,
            want=creg.disassemble(Other),
            meta=meta,
            converter=cattrs.Converter(),
            register=creg,
            creator=func3,
        )
        assert extractor.extract() == [o, 12, "one"]

        def func4(other: Other) -> strcs.ConvertResponse[Other]:
            ...

        extractor = strcs.ArgsExtractor(
            signature=inspect.signature(func4),
            value=val,
            want=creg.disassemble(Other),
            meta=meta,
            converter=cattrs.Converter(),
            register=creg,
            creator=func4,
        )
        assert extractor.extract() == [o]

    it "can get us the meta object", meta: strcs.Meta, creg: strcs.CreateRegister:

        def func(_meta) -> strcs.ConvertResponse[object]:
            ...

        val = mock.Mock(name="val")
        extractor = strcs.ArgsExtractor(
            signature=inspect.signature(func),
            value=val,
            want=creg.disassemble(object),
            meta=meta,
            converter=cattrs.Converter(),
            register=creg,
            creator=func,
        )

        assert extractor.extract() == [meta]

        def func2(_meta: strcs.Meta) -> strcs.ConvertResponse[object]:
            ...

        extractor = strcs.ArgsExtractor(
            signature=inspect.signature(func2),
            value=val,
            want=creg.disassemble(object),
            meta=meta,
            converter=cattrs.Converter(),
            register=creg,
            creator=func2,
        )

        assert extractor.extract() == [meta]

        def func3(val, /, _meta: strcs.Meta) -> strcs.ConvertResponse[object]:
            ...

        extractor = strcs.ArgsExtractor(
            signature=inspect.signature(func3),
            value=val,
            want=creg.disassemble(object),
            meta=meta,
            converter=cattrs.Converter(),
            register=creg,
            creator=func3,
        )

        assert extractor.extract() == [val, meta]

    it "can get us based just off the name of the argument", meta: strcs.Meta, creg: strcs.CreateRegister:

        class Other:
            pass

        o = Other()

        def func(
            value: object, want: strcs.Type, /, other, blah, stuff
        ) -> strcs.ConvertResponse[Other]:
            ...

        val = mock.Mock(name="val")
        meta["stuff"] = "one"
        meta["blah"] = 12
        meta["other"] = o

        extractor = strcs.ArgsExtractor(
            signature=inspect.signature(func),
            value=val,
            want=creg.disassemble(Other),
            meta=meta,
            converter=cattrs.Converter(),
            register=creg,
            creator=func,
        )
        assert extractor.extract() == [
            val,
            creg.disassemble(Other),
            o,
            12,
            "one",
        ]

    it "can get us the converter object", meta: strcs.Meta, creg: strcs.CreateRegister:

        def func(_converter) -> strcs.ConvertResponse[object]:
            ...

        val = mock.Mock(name="val")
        converter = cattrs.Converter()
        extractor = strcs.ArgsExtractor(
            signature=inspect.signature(func),
            value=val,
            want=creg.disassemble(object),
            meta=meta,
            converter=converter,
            register=creg,
            creator=func,
        )

        assert extractor.extract() == [converter]

        def func2(_converter: cattrs.Converter) -> strcs.ConvertResponse[object]:
            ...

        extractor = strcs.ArgsExtractor(
            signature=inspect.signature(func2),
            value=val,
            want=creg.disassemble(object),
            meta=meta,
            converter=converter,
            register=creg,
            creator=func2,
        )

        assert extractor.extract() == [converter]

        def func3(val, /, _converter: cattrs.Converter) -> strcs.ConvertResponse[object]:
            ...

        extractor = strcs.ArgsExtractor(
            signature=inspect.signature(func3),
            value=val,
            want=creg.disassemble(object),
            meta=meta,
            converter=converter,
            register=creg,
            creator=func3,
        )

        assert extractor.extract() == [val, converter]

    it "can get us the register object", meta: strcs.Meta, creg: strcs.CreateRegister:

        def func(_register) -> strcs.ConvertResponse[mock.Mock]:
            ...

        val = mock.Mock(name="val")
        extractor = strcs.ArgsExtractor(
            signature=inspect.signature(func),
            value=val,
            want=creg.disassemble(mock.Mock),
            meta=meta,
            converter=cattrs.Converter(),
            register=creg,
            creator=func,
        )

        assert extractor.extract() == [IsRegister(creg, mock.Mock, meta, func)]

        def func2(_register: strcs.CreateRegister) -> strcs.ConvertResponse[mock.Mock]:
            ...

        extractor = strcs.ArgsExtractor(
            signature=inspect.signature(func2),
            value=val,
            want=creg.disassemble(mock.Mock),
            meta=meta,
            converter=cattrs.Converter(),
            register=creg,
            creator=func2,
        )

        assert extractor.extract() == [IsRegister(creg, mock.Mock, meta, func2)]

        def func3(val, /, _register: strcs.CreateRegister) -> strcs.ConvertResponse[mock.Mock]:
            ...

        extractor = strcs.ArgsExtractor(
            signature=inspect.signature(func3),
            value=val,
            want=creg.disassemble(mock.Mock),
            meta=meta,
            converter=cattrs.Converter(),
            register=creg,
            creator=func3,
        )

        assert extractor.extract() == [val, IsRegister(creg, mock.Mock, meta, func3)]

    it "can get alternatives to the provided objects", type_cache: strcs.TypeCache:
        val = mock.Mock(name="val")

        register1 = strcs.CreateRegister(type_cache=type_cache)
        register2 = strcs.CreateRegister(type_cache=type_cache)

        converter1 = cattrs.Converter()
        converter2 = cattrs.Converter()

        meta1 = strcs.Meta()
        meta2 = strcs.Meta()

        meta1["register"] = register2
        meta1["converter"] = converter2
        meta1["meta"] = meta2

        def func(
            _register, register, _meta, meta, _converter, converter
        ) -> strcs.ConvertResponse[mock.Mock]:
            ...

        extractor = strcs.ArgsExtractor(
            signature=inspect.signature(func),
            value=val,
            want=register1.disassemble(mock.Mock),
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
        ) -> strcs.ConvertResponse[mock.Mock]:
            ...

        extractor = strcs.ArgsExtractor(
            signature=inspect.signature(func2),
            value=val,
            want=register1.disassemble(mock.Mock),
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
        ) -> strcs.ConvertResponse[mock.Mock]:
            ...

        extractor = strcs.ArgsExtractor(
            signature=inspect.signature(func3),
            value=val,
            want=register1.disassemble(mock.Mock),
            meta=meta1,
            converter=converter1,
            register=register1,
            creator=func3,
        )

        with pytest.raises(strcs.errors.FoundWithWrongType) as exc_info:
            extractor.extract()

        assert exc_info.value.args == (str, ["_register"])

    it "complains if it can't find something", meta: strcs.Meta, creg: strcs.CreateRegister:

        def func(wat) -> strcs.ConvertResponse[object]:
            ...

        extractor = strcs.ArgsExtractor(
            signature=inspect.signature(func),
            value=mock.Mock(name="val"),
            want=creg.disassemble(object),
            meta=meta,
            converter=cattrs.Converter(),
            register=creg,
            creator=func,
        )

        with pytest.raises(strcs.errors.NoDataByTypeName) as exc_info:
            extractor.extract()

        assert exc_info.value.args[1] == ["wat"]

        def func2(wat: int) -> strcs.ConvertResponse[object]:
            ...

        meta["one"] = 1
        meta["two"] = 2

        extractor = strcs.ArgsExtractor(
            signature=inspect.signature(func2),
            value=mock.Mock(name="val"),
            want=creg.disassemble(object),
            meta=meta,
            converter=cattrs.Converter(),
            register=creg,
            creator=func2,
        )

        with pytest.raises(strcs.errors.MultipleNamesForType) as exc_info2:
            extractor.extract()

        assert exc_info2.value.args[1] == ["one", "two"]
