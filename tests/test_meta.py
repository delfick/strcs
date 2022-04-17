# coding: spec

from strcs.meta import extract_type, Narrower

import typing as tp


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
