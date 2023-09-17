# coding: spec
import attrs
import pytest

from strcs.memoized_property import memoized_property

describe "memoized_property":
    it "memoizes":
        called: list[int] = []

        class Thing:
            _memoized_cache: dict[str, object]

            def __init__(self):
                self._memoized_cache = {}

            @memoized_property
            def blah(self) -> str:
                called.append(1)
                return "stuff"

        thing = Thing()
        assert thing.blah == "stuff"
        assert called == [1]
        assert thing.blah == "stuff"
        assert called == [1]
        assert thing.blah == "stuff"
        assert called == [1]

    it "works on an attrs class":
        called: list[int] = []

        @attrs.define
        class Thing:
            _memoized_cache: dict[str, object] = attrs.field(init=False, factory=lambda: {})

            @memoized_property
            def blah(self) -> str:
                called.append(1)
                return "stuff"

        thing = Thing()
        assert thing.blah == "stuff"
        assert called == [1]
        assert thing.blah == "stuff"
        assert called == [1]
        assert thing.blah == "stuff"
        assert called == [1]

    it "does not allow setting the value":
        called: list[int] = []

        class Thing:
            _memoized_cache: dict[str, object]

            def __init__(self):
                self._memoized_cache = {}

            @memoized_property
            def blah(self) -> str:
                called.append(1)
                return "stuff"

        thing = Thing()
        with pytest.raises(AttributeError):
            thing.blah = "other"

    it "allows deleting the value":
        called: list[int] = []

        class Thing:
            _memoized_cache: dict[str, object]

            def __init__(self):
                self._memoized_cache = {}

            @memoized_property
            def blah(self) -> str:
                called.append(1)
                return "stuff"

        thing = Thing()
        assert thing.blah == "stuff"
        assert called == [1]
        del thing.blah
        assert thing.blah == "stuff"
        assert called == [1, 1]
        assert thing.blah == "stuff"
        assert called == [1, 1]

    it "keeps the type annotation":

        class Thing:
            _memoized_cache: dict[str, object]

            def __init__(self):
                self._memoized_cache = {}

            @memoized_property
            def blah(self) -> str:
                return "stuff"

        def a(things: str) -> None:
            pass

        # will make mypy complain if it's broken
        a(Thing().blah)
