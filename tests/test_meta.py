# coding: spec

import secrets
import typing as tp

import cattrs
import pytest

import strcs
from strcs.meta import Meta, Narrower


@pytest.fixture(params=(True, False), ids=("with_cache", "without_cache"))
def type_cache(request: pytest.FixtureRequest) -> strcs.TypeCache:
    if request.param:
        return strcs.TypeCache()
    else:

        class Cache(strcs.TypeCache):
            def __setitem__(self, k: object, v: strcs.Type) -> None:
                return

        return Cache()


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
        assert meta.converter == IsConverter()
        assert meta.data == {}

        convs = cattrs.Converter()
        meta2 = Meta(converter=convs)
        assert meta2.converter is convs
        assert meta2.data == {}
        assert meta2.converter is not meta.converter

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

            assert old.converter is new.converter
            assert old.data == new.data

            self.assertCloned(old, new)

        it "can be cloned with a different converter":
            convs2 = cattrs.Converter()

            old = Meta()
            new = old.clone(converter=convs2)

            assert old.converter == IsConverter()
            assert new.converter is convs2
            assert old.converter is not new.converter
            assert old.data == new.data
            self.assertCloned(old, new)

        it "can be cloned with different data":
            old = Meta()
            old["b"] = 5
            new = old.clone(data_override={"a": 3})

            assert old.data == {"b": 5}
            assert new.data == {"a": 3}

            assert old.converter is new.converter
            self.assertCloned(old, new)

        it "can be cloned with extended data":
            old = Meta()
            old["b"] = 5
            new = old.clone({"a": 3})

            assert old.data == {"b": 5}
            assert new.data == {"b": 5, "a": 3}

            assert old.converter is new.converter
            self.assertCloned(old, new)

        it "can be cloned with new and extended data":
            old = Meta()
            old["b"] = 5

            override = {"c": 6}
            new = old.clone({"a": 3}, data_override=override)

            assert old.data == {"b": 5}
            assert new.data == {"c": 6, "a": 3}
            assert override == {"c": 6}

            assert old.converter is new.converter
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
        it "can return everything if type is object", type_cache: strcs.TypeCache:
            meta = Meta()
            meta.update({"a": 1, "b": 2})
            meta["c"] = 3

            assert meta.find_by_type(object, type_cache=type_cache) == (
                False,
                {"a": 1, "b": 2, "c": 3},
            )
            assert meta.find_by_type(tp.Optional[object], type_cache=type_cache) == (
                True,
                {"a": 1, "b": 2, "c": 3},
            )

        it "can be given the data to operate on", type_cache: strcs.TypeCache:
            meta = Meta()
            data = {"a": 1, "b": 2, "c": 3}

            assert meta.find_by_type(object, data=data, type_cache=type_cache) == (
                False,
                {"a": 1, "b": 2, "c": 3},
            )
            assert meta.find_by_type(tp.Optional[object], data=data, type_cache=type_cache) == (
                True,
                {"a": 1, "b": 2, "c": 3},
            )

        it "can find the correct type in meta", type_cache: strcs.TypeCache:
            meta = Meta()

            class Shape:
                pass

            class Square(Shape):
                pass

            square = Square()
            meta.update({"a": 1, "b": True, "c": 2.0, "d": "asdf", "e": square, "f": 20})

            assert meta.find_by_type(int, type_cache=type_cache) == (False, {"a": 1, "f": 20})
            assert meta.find_by_type(bool, type_cache=type_cache) == (False, {"b": True})
            assert meta.find_by_type(tp.Optional[bool], type_cache=type_cache) == (
                True,
                {"b": True},
            )
            assert meta.find_by_type(str, type_cache=type_cache) == (False, {"d": "asdf"})
            assert meta.find_by_type(Shape, type_cache=type_cache) == (False, {"e": square})
            assert meta.find_by_type(tp.Optional[Shape], type_cache=type_cache) == (
                True,
                {"e": square},
            )
            assert meta.find_by_type(tp.Union[int, float], type_cache=type_cache) == (
                False,
                {"a": 1, "c": 2.0, "f": 20},
            )
            assert meta.find_by_type(tp.Union[int, bool, float], type_cache=type_cache) == (
                False,
                {"a": 1, "b": True, "c": 2.0, "f": 20},
            )
            assert meta.find_by_type(tp.Optional[tp.Union[str, float]], type_cache=type_cache) == (
                True,
                {"d": "asdf", "c": 2.0},
            )

        it "can not find anything", type_cache: strcs.TypeCache:
            meta = Meta()
            meta["nup"] = None

            class Shape:
                pass

            assert meta.find_by_type(int, type_cache=type_cache) == (False, {})
            assert meta.find_by_type(bool, type_cache=type_cache) == (False, {})
            assert meta.find_by_type(tp.Optional[bool], type_cache=type_cache) == (True, {})
            assert meta.find_by_type(str, type_cache=type_cache) == (False, {})
            assert meta.find_by_type(Shape, type_cache=type_cache) == (False, {})
            assert meta.find_by_type(tp.Optional[Shape], type_cache=type_cache) == (True, {})
            assert meta.find_by_type(tp.Union[int, float], type_cache=type_cache) == (False, {})
            assert meta.find_by_type(tp.Union[int, bool, float], type_cache=type_cache) == (
                False,
                {},
            )
            assert meta.find_by_type(tp.Optional[tp.Union[str, float]], type_cache=type_cache) == (
                True,
                {},
            )

    describe "retrieve pattern":
        it "can retrieve based off patterns", type_cache: strcs.TypeCache:
            meta = strcs.Meta({"a": {"b": {"d": 4, "e": 5}}, "a.b": {"f": 6}, "a.bc": True})

            assert meta.retrieve_patterns(object, "a.b", type_cache=type_cache) == {"a.b": {"f": 6}}
            assert meta.retrieve_patterns(int, "a.b.d", "a.b.e", type_cache=type_cache) == {
                "a.b.d": 4,
                "a.b.e": 5,
            }
            assert meta.retrieve_patterns(object, "a.b.*", type_cache=type_cache) == {
                "a.b.d": 4,
                "a.b.e": 5,
                "a.b.f": 6,
            }
            assert meta.retrieve_patterns(object, "a.b*", type_cache=type_cache) == {
                "a.b": {"f": 6},
                "a.bc": True,
            }
            assert meta.retrieve_patterns(bool, "a.b*", type_cache=type_cache) == {"a.bc": True}
            assert meta.retrieve_patterns(object, type_cache=type_cache) == meta.data
            assert meta.retrieve_patterns(object, "d", type_cache=type_cache) == {}

    describe "retrieve one":
        it "can retrieve the one matching value", type_cache: strcs.TypeCache:
            meta = Meta()
            meta.update({"a": 1, "b": 2.0})

            assert meta.retrieve_one(int, type_cache=type_cache) == 1
            assert meta.retrieve_one(float, type_cache=type_cache) == 2.0

        it "can optionally retrieve the one value", type_cache: strcs.TypeCache:
            meta = Meta()
            meta["nup"] = "hello"

            assert (
                meta.retrieve_one(tp.Optional[int], refined_type=int, type_cache=type_cache) is None
            )

        it "can complain if there are 0 found values", type_cache: strcs.TypeCache:
            meta = Meta()
            meta["nup"] = None

            with pytest.raises(strcs.errors.NoDataByTypeName):
                meta.retrieve_one(int, type_cache=type_cache)

        it "can complain if there are more than 1 found values", type_cache: strcs.TypeCache:
            meta = Meta()
            meta.update({"a": 1, "b": 2})

            with pytest.raises(strcs.errors.MultipleNamesForType):
                meta.retrieve_one(int, type_cache=type_cache)

        it "can get the one value based on patterns too", type_cache: strcs.TypeCache:
            meta = Meta()
            meta.update({"a": 1, "b": 2})

            assert meta.retrieve_one(int, "a", type_cache=type_cache) == 1
            assert meta.retrieve_one(int, "b", type_cache=type_cache) == 2

            class Blah:
                pass

            blah = Blah()

            class Thing:
                e: tp.ClassVar[Blah] = blah

            meta["d"] = Thing()

            with pytest.raises(strcs.errors.NoDataByTypeName):
                assert meta.retrieve_one(Blah, type_cache=type_cache)

            assert meta.retrieve_one(Blah, "d.e", type_cache=type_cache) is blah

        it "can still find based just on type if patterns don't match", type_cache: strcs.TypeCache:
            meta = Meta()
            meta.update({"a": 1, "b": "asdf"})

            assert meta.retrieve_one(int, "c", type_cache=type_cache) == 1
            assert meta.retrieve_one(int, "d", type_cache=type_cache) == 1

        it "uses default if provided and found type but not name", type_cache: strcs.TypeCache:
            meta = Meta()
            meta.update({"a": 1, "b": 2})

            assert meta.retrieve_one(int, "a", default=30, type_cache=type_cache) == 1
            assert meta.retrieve_one(int, "d", default=40, type_cache=type_cache) == 40

        it "uses default if provided and found nothing", type_cache: strcs.TypeCache:
            meta = Meta()
            meta.update({"a": 1, "b": 2})

            assert meta.retrieve_one(float, "c", default=30, type_cache=type_cache) == 30
            assert meta.retrieve_one(float, "d", default=40, type_cache=type_cache) == 40

        it "complains if found name but type is wrong", type_cache: strcs.TypeCache:
            meta = Meta()
            meta.update({"a": 1, "b": 2})

            with pytest.raises(strcs.errors.FoundWithWrongType):
                meta.retrieve_one(float, "a", default=30, type_cache=type_cache)
