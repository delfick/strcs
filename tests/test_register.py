# coding: spec

import strcs

from unittest import mock
from attrs import define
import typing as tp
import cattrs
import pytest


@pytest.fixture()
def creg() -> strcs.CreateRegister:
    return strcs.CreateRegister()


class IsMeta:
    def __eq__(self, other):
        self.given = other
        return isinstance(other, strcs.Meta)

    def __repr__(self):
        if hasattr(self, "given"):
            if self == self.given:
                return repr(self.given)
            else:
                return f"<Given {type(self.given)}, expected a Meta>"
        return "<IsMeta?>"


class IsConverter:
    def __eq__(self, other):
        self.given = other
        return isinstance(other, cattrs.Converter)

    def __repr__(self):
        if hasattr(self, "given"):
            if self == self.given:
                return repr(self.given)
            else:
                return f"<Given {type(self.given)}, expected a Converter>"
        return "<IsConverter?>"


describe "Register":

    it "can register a convert function", creg: strcs.CreateRegister:

        @define
        class Thing:
            data: int

        @define
        class Stuff:
            info: str

        thing_maker = tp.cast(strcs.ConvertFunction, lambda v, w, m, c: {"data": 2})
        stuff_maker = tp.cast(strcs.ConvertFunction, lambda v, w, m, c: {"info": "hi"})

        assert creg.register == {}

        assert Thing not in creg
        creg[Thing] = thing_maker
        assert Thing in creg
        assert creg.register == {Thing: thing_maker}

        assert Stuff not in creg
        creg[Stuff] = stuff_maker
        assert Stuff in creg
        assert Thing in creg

        assert creg.register == {Thing: thing_maker, Stuff: stuff_maker}

    describe "can use the converters":
        it "works on anything", creg: strcs.CreateRegister:

            @define
            class Thing:
                pass

            thing = Thing()
            thing_maker = mock.Mock(name="thing_maker", return_value=thing)
            creg[Thing] = thing_maker
            assert creg.create(Thing) is thing
            thing_maker.assert_called_once_with(strcs.NotSpecified, Thing, IsMeta(), IsConverter())

            class Stuff:
                pass

            stuff = Stuff()
            stuff_maker = mock.Mock(name="stuff_maker", return_value=stuff)
            creg[Stuff] = stuff_maker
            assert creg.create(Stuff) is stuff
            stuff_maker.assert_called_once_with(strcs.NotSpecified, Stuff, IsMeta(), IsConverter())

        it "lets converter work on other types", creg: strcs.CreateRegister:

            @define
            class Other:
                name: str

            @define
            class Stuff:
                one: int
                two: int
                other: Other

            @define
            class Thing:
                number: int
                obj: Stuff

            thing_maker = mock.Mock(name="thing_maker")
            thing_maker.side_effect = lambda v, w, m, c: c.structure_attrs_fromdict(v, w)
            creg[Thing] = thing_maker

            value = {"number": 20, "obj": {"one": 20, "two": 50, "other": {"name": "there"}}}
            made = creg.create(Thing, value)
            thing_maker.assert_called_once_with(value, Thing, IsMeta(), IsConverter())
            assert isinstance(made, Thing)
            assert made.number == 20
            assert isinstance(made.obj, Stuff)
            assert made.obj.one == 20
            assert made.obj.two == 50
            assert isinstance(made.obj.other, Other)
            assert made.obj.other.name == "there"

        it "let's us convert a type that isn't in the register", creg: strcs.CreateRegister:

            @define
            class Stuff:
                one: int
                two: int

            @define
            class Other:
                name: str
                stuff: Stuff

            stuff_maker = mock.Mock(name="stuff_maker")
            stuff_maker.side_effect = lambda v, w, m, c: c.structure_attrs_fromdict(v, w)
            creg[Stuff] = stuff_maker

            value = {"name": "hi", "stuff": {"one": 45, "two": 76}}
            made = creg.create(Other, value)
            stuff_maker.assert_called_once_with(
                {"one": 45, "two": 76}, Stuff, IsMeta(), IsConverter()
            )
            assert isinstance(made, Other)
            assert made.name == "hi"
            assert isinstance(made.stuff, Stuff)
            assert made.stuff.one == 45
            assert made.stuff.two == 76

        it "let's us convert with super types", creg: strcs.CreateRegister:

            @define
            class Shape:
                three: int
                one: int = 1
                two: int = 2

            @define
            class Triangle(Shape):
                three: int
                one: int = 20
                two: int = 45

            @define
            class Square(Shape):
                three: int
                one: int = 33
                two: int = 22

            meta = strcs.Meta()
            meta["three"] = 100

            shape_maker = mock.Mock(name="shape_maker")
            shape_maker.side_effect = lambda v, w, m, c: c.structure_attrs_fromdict(
                {"three": meta.retrieve_one(int, "three")}, w
            )
            creg[Shape] = shape_maker

            assert Square in creg
            assert Shape in creg
            assert Triangle in creg
            assert mock.Mock not in creg

            made = creg.create(Square, meta=meta)
            assert isinstance(made, Square)
            assert made.one == 33
            assert made.two == 22
            assert made.three == 100
            shape_maker.assert_called_once_with(strcs.NotSpecified, Square, meta, IsConverter())
            shape_maker.reset_mock()

            made = creg.create(Triangle, meta=meta)
            assert isinstance(made, Triangle)
            assert made.one == 20
            assert made.two == 45
            assert made.three == 100
            shape_maker.assert_called_once_with(strcs.NotSpecified, Triangle, meta, IsConverter())
            shape_maker.reset_mock()

            made = creg.create(Shape, meta=meta)
            assert isinstance(made, Shape)
            assert made.one == 1
            assert made.two == 2
            assert made.three == 100
            shape_maker.assert_called_once_with(strcs.NotSpecified, Shape, meta, IsConverter())
            shape_maker.reset_mock()

        it "doesn't fail on checking against a not type in the register", creg: strcs.CreateRegister:

            @define
            class Thing:
                pass

            assert Thing not in creg
            assert tp.cast(tp.Type, Thing()) not in creg

            creg[Thing] = tp.cast(strcs.ConvertFunction, mock.Mock(name="creator"))
            assert Thing in creg
            assert tp.cast(tp.Type, Thing()) not in creg
