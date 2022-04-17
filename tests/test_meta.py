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
