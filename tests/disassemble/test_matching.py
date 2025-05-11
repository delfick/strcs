import dataclasses
import random
from collections.abc import Generator
from unittest import mock

import attrs

import strcs

Disassembler = strcs.disassemble.Disassembler


class TestMatchingAType:
    def make_functions(
        self, types: dict[int | str, object], *, Dis: Disassembler
    ) -> list[tuple[strcs.Type, strcs.ConvertFunction]]:
        reg = strcs.CreateRegister(type_cache=Dis.type_cache)

        for name, typ in types.items():
            reg[Dis(typ)] = getattr(mock.sentinel, f"function_{name}")

        return list(reg.register.items())

    def shuffles(
        self, inp: list[tuple[strcs.Type, strcs.ConvertFunction]]
    ) -> Generator[list[tuple[strcs.Type, strcs.ConvertFunction]]]:
        shuffling = list(inp)
        for _ in range(5):
            random.shuffle(shuffling)
            yield shuffling

    def test_it_finds_the_basic_type(self, Dis: Disassembler):
        typ = Dis(int)
        available = self.make_functions({0: str, 1: bool, 2: float, 3: int}, Dis=Dis)
        for ordered in self.shuffles(available):
            assert typ.func_from(ordered) is mock.sentinel.function_3

    def test_it_finds_the_matching_attrs_dataclass_normal_class(self, Dis: Disassembler):
        @attrs.define
        class Thing:
            pass

        @dataclasses.dataclass
        class Stuff:
            pass

        class Blah:
            pass

        available = self.make_functions({0: Stuff, 1: Thing, 2: Blah}, Dis=Dis)

        for ordered in self.shuffles(available):
            typ = Dis(Thing)
            assert typ.func_from(ordered) is mock.sentinel.function_1

            typ = Dis(Stuff)
            assert typ.func_from(ordered) is mock.sentinel.function_0

            typ = Dis(Blah)
            assert typ.func_from(ordered) is mock.sentinel.function_2

    def test_it_finds_the_matching_attrs_dataclass_normal_subclass(self, Dis: Disassembler):
        @attrs.define
        class Thing:
            pass

        @attrs.define
        class ChildThing(Thing):
            pass

        @dataclasses.dataclass
        class Stuff:
            pass

        @dataclasses.dataclass
        class ChildStuff(Stuff):
            pass

        class Blah:
            pass

        class ChildBlah(Blah):
            pass

        available = self.make_functions({0: Stuff, 1: Thing, 2: Blah}, Dis=Dis)
        for ordered in self.shuffles(available):
            typ = Dis(ChildThing)
            assert typ.func_from(ordered) is mock.sentinel.function_1
            del typ

            typ = Dis(ChildStuff)
            assert typ.func_from(ordered) is mock.sentinel.function_0
            del typ

            typ = Dis(ChildBlah)
            assert typ.func_from(ordered) is mock.sentinel.function_2
            del typ

    def test_it_finds_the_matching_child_attrs_dataclass_normal(self, Dis: Disassembler):
        @attrs.define
        class Thing:
            pass

        @attrs.define
        class ChildThing(Thing):
            pass

        @dataclasses.dataclass
        class Stuff:
            pass

        @dataclasses.dataclass
        class ChildStuff(Stuff):
            pass

        class Blah:
            pass

        class ChildBlah(Blah):
            pass

        available = self.make_functions(
            {0: Stuff, 1: Thing, 2: Blah, 3: ChildThing, 4: ChildStuff}, Dis=Dis
        )
        for ordered in self.shuffles(available):
            typ = Dis(Thing)
            assert typ.func_from(ordered) is mock.sentinel.function_1
            del typ

            typ = Dis(ChildThing)
            assert typ.func_from(ordered) is mock.sentinel.function_3
            del typ

            typ = Dis(Stuff)
            assert typ.func_from(ordered) is mock.sentinel.function_0
            del typ

            typ = Dis(ChildStuff)
            assert typ.func_from(ordered) is mock.sentinel.function_4
            del typ

            typ = Dis(Blah)
            assert typ.func_from(ordered) is mock.sentinel.function_2
            del typ

            typ = Dis(ChildBlah)
            assert typ.func_from(ordered) is mock.sentinel.function_2
            del typ

    def test_it_finds_union_type_before_matching_against_first_function(self, Dis: Disassembler):
        @attrs.define
        class Thing:
            pass

        @attrs.define
        class ChildThing(Thing):
            pass

        @dataclasses.dataclass
        class Stuff:
            pass

        @dataclasses.dataclass
        class ChildStuff(Stuff):
            pass

        class Blah:
            pass

        class ChildBlah(Blah):
            pass

        available = self.make_functions({0: Stuff | Thing, 2: Stuff}, Dis=Dis)
        for ordered in self.shuffles(available):
            typ = Dis(ChildBlah)
            assert typ.func_from(ordered) is None
            del typ

            typ = Dis(Blah)
            assert typ.func_from(ordered) is None
            del typ

            typ = Dis(Stuff | Thing)
            assert typ.func_from(ordered) is mock.sentinel.function_0
            del typ

            typ = Dis(ChildStuff | ChildThing)
            assert typ.func_from(ordered) is mock.sentinel.function_0
            del typ

            typ = Dis(Stuff)
            assert typ.func_from(ordered) is mock.sentinel.function_0
            del typ

            typ = Dis(Thing)
            assert typ.func_from(ordered) is mock.sentinel.function_0
            del typ

    def test_it_can_match_a_subclass_of_a_filled_generic(self, Dis: Disassembler):
        available = self.make_functions({0: dict, 1: dict[str, dict], 2: dict[str, str]}, Dis=Dis)

        class D(dict[str, str]):
            pass

        typ = Dis(D)
        assert typ.func_from(available) is mock.sentinel.function_2
