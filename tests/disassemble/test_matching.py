# coding: spec

import random
import typing as tp
from dataclasses import dataclass
from unittest import mock

import pytest
from attrs import define

import strcs


@pytest.fixture()
def type_cache() -> strcs.TypeCache:
    return strcs.TypeCache()


describe "Matching a Type":

    def make_functions(
        self, types: dict[int | str, object], cache: strcs.TypeCache
    ) -> list[tuple[strcs.Type, strcs.ConvertFunction]]:
        reg = strcs.CreateRegister(type_cache=cache)

        for name, typ in types.items():
            reg[strcs.Type.create(typ, cache=cache)] = getattr(mock.sentinel, f"function_{name}")

        return list(reg.register.items())

    def shuffles(
        self, inp: list[tuple[strcs.Type, strcs.ConvertFunction]]
    ) -> tp.Generator[list[tuple[strcs.Type, strcs.ConvertFunction]], None, None]:
        shuffling = list(inp)
        for _ in range(5):
            random.shuffle(shuffling)
            yield shuffling

    it "finds the basic type", type_cache: strcs.TypeCache:
        typ = strcs.Type.create(int, cache=type_cache, expect=int)
        available = self.make_functions({0: str, 1: bool, 2: float, 3: int}, cache=type_cache)
        for ordered in self.shuffles(available):
            assert typ.func_from(ordered) is mock.sentinel.function_3

    it "finds the matching attrs/dataclass/normal class", type_cache: strcs.TypeCache:

        @define
        class Thing:
            pass

        @dataclass
        class Stuff:
            pass

        class Blah:
            pass

        available = self.make_functions({0: Stuff, 1: Thing, 2: Blah}, cache=type_cache)

        for ordered in self.shuffles(available):

            typ = strcs.Type.create(Thing, cache=type_cache, expect=Thing)
            assert typ.func_from(ordered) is mock.sentinel.function_1

            typ = strcs.Type.create(Stuff, cache=type_cache, expect=Stuff)
            assert typ.func_from(ordered) is mock.sentinel.function_0

            typ = strcs.Type.create(Blah, cache=type_cache, expect=Blah)
            assert typ.func_from(ordered) is mock.sentinel.function_2

    it "finds the matching attrs/dataclass/normal subclass", type_cache: strcs.TypeCache:

        @define
        class Thing:
            pass

        @define
        class ChildThing(Thing):
            pass

        @dataclass
        class Stuff:
            pass

        @dataclass
        class ChildStuff(Stuff):
            pass

        class Blah:
            pass

        class ChildBlah(Blah):
            pass

        available = self.make_functions({0: Stuff, 1: Thing, 2: Blah}, cache=type_cache)
        for ordered in self.shuffles(available):
            typ = strcs.Type.create(ChildThing, cache=type_cache, expect=ChildThing)
            assert typ.func_from(ordered) is mock.sentinel.function_1
            del typ

            typ = strcs.Type.create(ChildStuff, cache=type_cache, expect=ChildStuff)
            assert typ.func_from(ordered) is mock.sentinel.function_0
            del typ

            typ = strcs.Type.create(ChildBlah, cache=type_cache, expect=ChildBlah)
            assert typ.func_from(ordered) is mock.sentinel.function_2
            del typ

    it "finds the matching child attrs/dataclass/normal", type_cache: strcs.TypeCache:

        @define
        class Thing:
            pass

        @define
        class ChildThing(Thing):
            pass

        @dataclass
        class Stuff:
            pass

        @dataclass
        class ChildStuff(Stuff):
            pass

        class Blah:
            pass

        class ChildBlah(Blah):
            pass

        available = self.make_functions(
            {0: Stuff, 1: Thing, 2: Blah, 3: ChildThing, 4: ChildStuff}, cache=type_cache
        )
        for ordered in self.shuffles(available):
            typ = strcs.Type.create(Thing, cache=type_cache, expect=Thing)
            assert typ.func_from(ordered) is mock.sentinel.function_1
            del typ

            typ = strcs.Type.create(ChildThing, cache=type_cache, expect=ChildThing)
            assert typ.func_from(ordered) is mock.sentinel.function_3
            del typ

            typ = strcs.Type.create(Stuff, cache=type_cache, expect=Stuff)
            assert typ.func_from(ordered) is mock.sentinel.function_0
            del typ

            typ = strcs.Type.create(ChildStuff, cache=type_cache, expect=ChildStuff)
            assert typ.func_from(ordered) is mock.sentinel.function_4
            del typ

            typ = strcs.Type.create(Blah, cache=type_cache, expect=Blah)
            assert typ.func_from(ordered) is mock.sentinel.function_2
            del typ

            typ = strcs.Type.create(ChildBlah, cache=type_cache, expect=ChildBlah)
            assert typ.func_from(ordered) is mock.sentinel.function_2
            del typ

    it "finds union type before matching against first function", type_cache: strcs.TypeCache:

        @define
        class Thing:
            pass

        @define
        class ChildThing(Thing):
            pass

        @dataclass
        class Stuff:
            pass

        @dataclass
        class ChildStuff(Stuff):
            pass

        class Blah:
            pass

        class ChildBlah(Blah):
            pass

        available = self.make_functions({0: Stuff | Thing, 2: Stuff}, cache=type_cache)
        for ordered in self.shuffles(available):
            typ = strcs.Type.create(ChildBlah, cache=type_cache, expect=ChildBlah)
            assert typ.func_from(ordered) is None
            del typ

            typ = strcs.Type.create(Blah, cache=type_cache, expect=Blah)
            assert typ.func_from(ordered) is None
            del typ

            typ: strcs.Type[Stuff | Thing] = strcs.Type.create(Stuff | Thing, cache=type_cache)
            assert typ.func_from(ordered) is mock.sentinel.function_0
            del typ

            typ: strcs.Type[ChildStuff | ChildThing] = strcs.Type.create(
                ChildStuff | ChildThing, cache=type_cache
            )
            assert typ.func_from(ordered) is mock.sentinel.function_0
            del typ

            typ = strcs.Type.create(Stuff, cache=type_cache, expect=Stuff)
            assert typ.func_from(ordered) is mock.sentinel.function_2
            del typ

            typ = strcs.Type.create(Thing, cache=type_cache, expect=Stuff)
            assert typ.func_from(ordered) is mock.sentinel.function_0
            del typ

    it "can match a subclass of a filled generic", type_cache: strcs.TypeCache:
        available = self.make_functions(
            {0: dict, 1: dict[str, dict], 2: dict[str, str]}, cache=type_cache
        )

        class D(dict[str, str]):
            pass

        typ = strcs.Type.create(D, expect=D, cache=type_cache)
        assert typ.func_from(available) is mock.sentinel.function_2
