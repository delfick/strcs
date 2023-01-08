# coding: spec

from strcs.memoized_property import memoized_property

describe "memoized_property":
    it "memoizes":
        called: list[int] = []

        class Thing:
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

    it "allows setting the value":
        called: list[int] = []

        class Thing:
            @memoized_property
            def blah(self) -> str:
                called.append(1)
                return "stuff"

        thing = Thing()
        assert thing.blah == "stuff"
        assert called == [1]
        thing.blah = "other"
        assert thing.blah == "other"
        assert called == [1]
        assert thing.blah == "other"
        assert called == [1]

    it "allows deleting the value":
        called: list[int] = []

        class Thing:
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
            @memoized_property
            def blah(self) -> str:
                return "stuff"

        def a(things: str) -> None:
            pass

        # will make mypy complain if it's broken
        a(Thing().blah)
