# coding: spec

from strcs.meta import extract_type, Narrower, Meta
import strcs

import typing as tp
import secrets
import pytest
import cattrs


describe "extract_type":
    it "can return the type and that it isn't optional when not optional":
        assert extract_type(list[str]) == (False, list[str])
        assert extract_type(str | bool) == (False, str | bool)
        assert extract_type(tp.Annotated[int, "stuff"]) == (False, tp.Annotated[int, "stuff"])

        T = tp.TypeVar("T")
        assert extract_type(T) == (False, T)

        class Thing:
            pass

        assert extract_type(Thing) == (False, Thing)

        extract_type("asdf") == (False, "asdf")

    it "can return the embedded type and that it is optional when is optional":
        assert extract_type(tp.Optional[list[str]]) == (True, list[str])
        assert extract_type(tp.Optional[str | bool]) == (True, str | bool)
        assert extract_type(tp.Optional[tp.Annotated[int, "stuff"]]) == (
            True,
            tp.Annotated[int, "stuff"],
        )

        T = tp.TypeVar("T")
        assert extract_type(tp.Optional[T]) == (True, T)

        class Thing:
            pass

        assert extract_type(tp.Optional[Thing]) == (True, Thing)

describe "Narrower":
    describe "narrow":

        it "can return a copy of the dictionary with matching options":
            a = {"a": 1, "b": 2, "c": 3}

            assert Narrower(a).narrow("a") == {"a": 1}
            assert Narrower(a).narrow("f") == {}

            assert a == Narrower(a).narrow("*") == {"a": 1, "b": 2, "c": 3}

            a = {"a": 1, "aa": 2, "baa": 3}
            assert Narrower(a).narrow("a*") == {"a": 1, "aa": 2}
            assert Narrower(a).narrow("*") == {"a": 1, "aa": 2, "baa": 3}
            assert Narrower(a).narrow() == {}

        it "can return a copy of the dictionary with nested options":
            a = {"a": 1, "b": 2, "c": {"d": 3, "e": {"f": 5}, "g": 6}, "h": 7}

            assert Narrower(a).narrow("c.e.f") == {"c.e.f": 5}
            assert Narrower(a).narrow("c.g", "c.e.f") == {"c.e.f": 5, "c.g": 6}
            assert Narrower(a).narrow("h", "c.e.f") == {"c.e.f": 5, "h": 7}
            assert Narrower(a).narrow("h.g", "c.e.f") == {"c.e.f": 5}
            assert Narrower(a).narrow("a.e.f") == {}

            assert (
                a
                == Narrower(a).narrow("*")
                == {"a": 1, "b": 2, "c": {"d": 3, "e": {"f": 5}, "g": 6}, "h": 7}
            )

        it "will match dotted keys before nested objects":
            obj = {"a": {"b": {"d": 4, "e": 5}}, "a.b": 1, "a.c": 3}
            assert Narrower(obj).narrow("a.b") == {"a.b": 1}
            assert Narrower(obj).narrow("a.c") == {"a.c": 3}
            assert Narrower(obj).narrow("a.b.d") == {"a.b.d": 4}
            assert Narrower(obj).narrow("a.b.*") == {"a.b.d": 4, "a.b.e": 5}
            assert Narrower(obj).narrow("a.b*") == {"a.b": 1}

            obj = {"a": {"b": {"d": 4, "e": 5}}, "a.b": {"f": 6}, "a.bc": True}
            assert Narrower(obj).narrow("a.b") == {"a.b": {"f": 6}}
            assert Narrower(obj).narrow("a.b.d") == {"a.b.d": 4}
            assert Narrower(obj).narrow("a.b.*") == {"a.b.d": 4, "a.b.e": 5, "a.b.f": 6}
            assert Narrower(obj).narrow("a.b*") == {"a.b": {"f": 6}, "a.bc": True}

        it "can return a copy of the dictionary with nested objects":

            class Store:
                def __init__(self, e):
                    self.e = e
                    self.f = [7, 8]

            class Config:
                class Thing:
                    a = 2

                class Other:
                    b = [3, 4]

                    class Tree:
                        c = [Store(5), Store(6)]
                        d = 7

                c = 4

            config = Config()
            a = {"config": config}

            assert Narrower(a).narrow("config") == {"config": config}
            assert Narrower(a).narrow("config.c") == {"config.c": 4}
            assert Narrower(a).narrow("config.c", "config.c") == {
                "config.c": 4,
            }
            assert Narrower(a).narrow("config.Thing.a", "config.Thing") == {
                "config.Thing.a": 2,
                "config.Thing": config.Thing,
            }
            assert Narrower(a).narrow("config.Thing.a", "config.Thing", "config.Other.Tree.*") == {
                "config.Thing.a": 2,
                "config.Thing": config.Thing,
                "config.Other.Tree.c": [config.Other.Tree.c[0], config.Other.Tree.c[1]],
                "config.Other.Tree.d": 7,
            }

            assert a == Narrower(a).narrow("*") == {"config": config}

describe "Meta":
    it "can be created":
        meta = Meta()
        assert meta._converter is strcs.converter
        assert meta.data == {}

        convs = cattrs.Converter()
        meta = Meta(converter=convs)
        assert meta._converter is convs
        assert meta.data == {}

    describe "cloning":

        def assertCloned(self, old: Meta, new: Meta) -> None:
            data_old = old.data
            data_new = new.data
            assert data_old is not data_new

            key = secrets.token_hex(64)
            value = secrets.token_hex(64)
            assert key not in data_old
            assert key not in data_new
            old[key] = value
            assert data_old[key] == value
            assert key not in data_new

            key = secrets.token_hex(64)
            value = secrets.token_hex(64)
            assert key not in data_old
            assert key not in data_new
            new[key] = value
            assert key not in data_old
            assert data_new[key] == value

        it "can be cloned":
            old = Meta()
            new = old.clone()

            assert old._converter is new._converter
            assert old.data == new.data

            self.assertCloned(old, new)

        it "can be cloned with a different converter":
            convs2 = cattrs.Converter()

            old = Meta()
            new = old.clone(converter=convs2)

            assert old._converter is strcs.converter
            assert new._converter is convs2
            assert old.data == new.data
            self.assertCloned(old, new)

        it "can be cloned with different data":
            old = Meta()
            old["b"] = 5
            new = old.clone(data_override={"a": 3})

            assert old.data == {"b": 5}
            assert new.data == {"a": 3}

            assert old._converter is new._converter
            self.assertCloned(old, new)

        it "can be cloned with extended data":
            old = Meta()
            old["b"] = 5
            new = old.clone(data_extra={"a": 3})

            assert old.data == {"b": 5}
            assert new.data == {"b": 5, "a": 3}

            assert old._converter is new._converter
            self.assertCloned(old, new)

        it "can be cloned with new and extended data":
            old = Meta()
            old["b"] = 5

            override = {"c": 6}
            new = old.clone(data_override=override, data_extra={"a": 3})

            assert old.data == {"b": 5}
            assert new.data == {"c": 6, "a": 3}
            assert override == {"c": 6}

            assert old._converter is new._converter
            self.assertCloned(old, new)

    describe "Changing data":
        it "can have data added":
            meta = Meta()
            assert meta.data == {}

            assert "a" not in meta
            meta["a"] = 3
            assert meta.data == {"a": 3}
            assert "a" in meta

            Thing = type("Thing", (), {})
            thing = Thing()
            assert "asdf" not in meta
            meta["asdf"] = thing
            assert "asdf" in meta
            assert meta.data == {"a": 3, "asdf": thing}

            other = Thing()
            meta["asdf"] = other
            assert meta.data == {"a": 3, "asdf": other}

            other = Thing()
            meta["asdf"] = 3
            assert "asdf" in meta
            assert meta.data == {"a": 3, "asdf": 3}

        it "can remove a name from meta":
            meta = Meta()
            assert meta.data == {}

            assert "a" not in meta
            meta["a"] = 3
            assert meta.data == {"a": 3}
            del meta["a"]
            assert meta.data == {}

            meta["b"] = 4
            meta["c"] = 5
            assert meta.data == {"b": 4, "c": 5}
            assert "a" not in meta
            assert "b" in meta
            assert "c" in meta

            del meta["b"]
            assert "a" not in meta
            assert "b" not in meta
            assert "c" in meta

        it "can bulk update data":
            meta = Meta()
            assert meta.data == {}

            meta.update({"a": 1, "b": 3, "c": 3})
            assert meta.data == {"a": 1, "b": 3, "c": 3}

            meta.update({"b": 2, "d": 4})
            assert meta.data == {"a": 1, "b": 2, "c": 3, "d": 4}

    describe "find_by_type":
        it "can return everything if type is object":
            meta = Meta()
            meta.update({"a": 1, "b": 2})
            meta["c"] = 3

            assert meta.find_by_type(object) == (False, {"a": 1, "b": 2, "c": 3})
            assert meta.find_by_type(tp.Optional[object]) == (True, {"a": 1, "b": 2, "c": 3})

        it "can be given the data to operate on":
            meta = Meta()
            data = {"a": 1, "b": 2, "c": 3}

            assert meta.find_by_type(object, data=data) == (False, {"a": 1, "b": 2, "c": 3})
            assert meta.find_by_type(tp.Optional[object], data=data) == (
                True,
                {"a": 1, "b": 2, "c": 3},
            )

        it "can find the correct type in meta":
            meta = Meta()

            class Shape:
                pass

            class Square(Shape):
                pass

            square = Square()
            meta.update({"a": 1, "b": True, "c": 2.0, "d": "asdf", "e": square, "f": 20})

            assert meta.find_by_type(int) == (False, {"a": 1, "f": 20})
            assert meta.find_by_type(bool) == (False, {"b": True})
            assert meta.find_by_type(tp.Optional[bool]) == (True, {"b": True})
            assert meta.find_by_type(str) == (False, {"d": "asdf"})
            assert meta.find_by_type(Shape) == (False, {"e": square})
            assert meta.find_by_type(tp.Optional[Shape]) == (True, {"e": square})
            assert meta.find_by_type(tp.Union[int, float]) == (False, {"a": 1, "c": 2.0, "f": 20})
            assert meta.find_by_type(tp.Union[int, bool, float]) == (
                False,
                {"a": 1, "b": True, "c": 2.0, "f": 20},
            )
            assert meta.find_by_type(tp.Optional[tp.Union[str, float]]) == (
                True,
                {"d": "asdf", "c": 2.0},
            )

        it "can not find anything":
            meta = Meta()
            meta["nup"] = None

            class Shape:
                pass

            assert meta.find_by_type(int) == (False, {})
            assert meta.find_by_type(bool) == (False, {})
            assert meta.find_by_type(tp.Optional[bool]) == (True, {})
            assert meta.find_by_type(str) == (False, {})
            assert meta.find_by_type(Shape) == (False, {})
            assert meta.find_by_type(tp.Optional[Shape]) == (True, {})
            assert meta.find_by_type(tp.Union[int, float]) == (False, {})
            assert meta.find_by_type(tp.Union[int, bool, float]) == (False, {})
            assert meta.find_by_type(tp.Optional[tp.Union[str, float]]) == (True, {})

    describe "retrieve one":
        it "can retrieve the one matching value":
            meta = Meta()
            meta.update({"a": 1, "b": 2.0})

            assert meta.retrieve_one(int) == 1
            assert meta.retrieve_one(float) == 2.0

        it "can optionally retrieve the one value":
            meta = Meta()
            meta["nup"] = "hello"

            assert meta.retrieve_one(tp.Optional[int]) is None

        it "can complain if there are 0 found values":
            meta = Meta()
            meta["nup"] = None

            with pytest.raises(strcs.errors.NoDataByTypeName):
                meta.retrieve_one(int)

        it "can complain if there are more than 1 found values":
            meta = Meta()
            meta.update({"a": 1, "b": 2})

            with pytest.raises(strcs.errors.MultipleNamesForType):
                meta.retrieve_one(int)

        it "can get the one value based on patterns too":
            meta = Meta()
            meta.update({"a": 1, "b": 2})

            assert meta.retrieve_one(int, "a") == 1
            assert meta.retrieve_one(int, "b") == 2

            class Blah:
                pass

            blah = Blah()

            class Thing:
                e: Blah = blah

            meta["d"] = Thing()

            with pytest.raises(strcs.errors.NoDataByTypeName):
                assert meta.retrieve_one(Blah)

            assert meta.retrieve_one(Blah, "d.e") is blah

        it "can still find based just on type if patterns don't match":
            meta = Meta()
            meta.update({"a": 1, "b": "asdf"})

            assert meta.retrieve_one(int, "c") == 1
            assert meta.retrieve_one(int, "d") == 1
