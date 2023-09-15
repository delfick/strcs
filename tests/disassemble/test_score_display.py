# coding: spec
import dataclasses
import itertools
import sys
import textwrap
import types
import typing as tp

import attrs
import pytest

import strcs
from strcs import Type


@pytest.fixture()
def type_cache() -> strcs.TypeCache:
    return strcs.TypeCache()


T = tp.TypeVar("T")
U = tp.TypeVar("U")

describe "Type":

    def assertDisplay(self, disassembled: Type, expected: str) -> None:
        got = disassembled.score.for_display(indent="  ").strip()
        want = "\n".join(f"  {line}" for line in textwrap.dedent(expected).split("\n")).strip()
        if got != want:
            for i, (g, w) in enumerate(itertools.zip_longest(got.split("\n"), want.split("\n"))):
                cross = "x" if g != w else "✓"
                print(f"{cross}:{i}    -----")
                print(f"  got : {str(g).replace(' ', '.')}")
                print(f"  want: {str(w).replace(' ', '.')}")

        assert got == want

    it "works on None", type_cache: strcs.TypeCache:
        provided = None
        disassembled = Type.create(provided, expect=type(None), cache=type_cache)
        self.assertDisplay(
            disassembled,
            """
          x Union optional
          x Union
          x Annotated
          0 typevars ()
          x Typevars
          x Optional
          2 MRO length
          ✓ Origin MRO:
            *  custom: False
               name: NoneType
               module: builtins
               package:
            *  custom: False
               name: object
               module: builtins
               package:
        """,
        )

    it "doesn't overcome python limitations with annotating None and thinks we annotated type of None", type_cache: strcs.TypeCache:
        provided = tp.Annotated[None, 1]
        disassembled = Type.create(provided, expect=type(None), cache=type_cache)
        self.assertDisplay(
            disassembled,
            """
          x Union optional
          x Union
          ✓ Annotated
          0 typevars ()
          x Typevars
          x Optional
          2 MRO length
          ✓ Origin MRO:
            *  custom: False
               name: NoneType
               module: builtins
               package:
            *  custom: False
               name: object
               module: builtins
               package:
        """,
        )

    it "works on simple type", type_cache: strcs.TypeCache:
        provided = int
        disassembled = Type.create(provided, expect=int, cache=type_cache)
        self.assertDisplay(
            disassembled,
            """
          x Union optional
          x Union
          x Annotated
          0 typevars ()
          x Typevars
          x Optional
          2 MRO length
          ✓ Origin MRO:
            *  custom: False
               name: int
               module: builtins
               package:
            *  custom: False
               name: object
               module: builtins
               package:
        """,
        )

    it "works on a union", type_cache: strcs.TypeCache:
        provided = int | str
        disassembled = Type.create(provided, expect=types.UnionType, cache=type_cache)
        self.assertDisplay(
            disassembled,
            """
          x Union optional
          2 Union length
          ✓ Union:
            *  x Union optional
               x Union
               x Annotated
               0 typevars ()
               x Typevars
               x Optional
               2 MRO length
               ✓ Origin MRO:
                 *  custom: False
                    name: str
                    module: builtins
                    package:
                 *  custom: False
                    name: object
                    module: builtins
                    package:
            *  x Union optional
               x Union
               x Annotated
               0 typevars ()
               x Typevars
               x Optional
               2 MRO length
               ✓ Origin MRO:
                 *  custom: False
                    name: int
                    module: builtins
                    package:
                 *  custom: False
                    name: object
                    module: builtins
                    package:
          x Annotated
          0 typevars ()
          x Typevars
          x Optional
          2 MRO length
          ✓ Origin MRO:
            *  custom: True
               name: UnionType
               module: types
               package:
            *  custom: False
               name: object
               module: builtins
               package:
        """,
        )

    @pytest.mark.skipif(sys.version_info < (3, 11), reason="requires python3.11 or higher")
    it "works on a complicated union", type_cache: strcs.TypeCache:
        provided = tp.Union[
            tp.Annotated[list[int], "str"], tp.Annotated[int | str | None, '"hello']
        ]
        disassembled = Type.create(provided, expect=types.UnionType, cache=type_cache)
        self.assertDisplay(
            disassembled,
            """
          x Union optional
          2 Union length
          ✓ Union:
            *  ✓ Annotated Union:
                 *  x Union optional
                    x Union
                    x Annotated
                    0 typevars ()
                    x Typevars
                    x Optional
                    2 MRO length
                    ✓ Origin MRO:
                      *  custom: False
                         name: str
                         module: builtins
                         package:
                      *  custom: False
                         name: object
                         module: builtins
                         package:
                 *  x Union optional
                    x Union
                    x Annotated
                    0 typevars ()
                    x Typevars
                    x Optional
                    2 MRO length
                    ✓ Origin MRO:
                      *  custom: False
                         name: int
                         module: builtins
                         package:
                      *  custom: False
                         name: object
                         module: builtins
                         package:
               ✓ Union optional
               2 Union length
               ✓ Annotated
               0 typevars ()
               x Typevars
               ✓ Optional
               2 MRO length
               ✓ Origin MRO:
                 *  custom: True
                    name: UnionType
                    module: types
                    package:
                 *  custom: False
                    name: object
                    module: builtins
                    package:
            *  x Union optional
               x Union
               ✓ Annotated
               1 typevars (True,)
               ✓ Typevars:
                 *  x Union optional
                    x Union
                    x Annotated
                    0 typevars ()
                    x Typevars
                    x Optional
                    2 MRO length
                    ✓ Origin MRO:
                      *  custom: False
                         name: int
                         module: builtins
                         package:
                      *  custom: False
                         name: object
                         module: builtins
                         package:
               x Optional
               2 MRO length
               ✓ Origin MRO:
                 *  custom: False
                    name: list
                    module: builtins
                    package:
                 *  custom: False
                    name: object
                    module: builtins
                    package:
          x Annotated
          0 typevars ()
          x Typevars
          x Optional
          6 MRO length
          ✓ Origin MRO:
            *  custom: True
               name: _UnionGenericAlias
               module: typing
               package:
            *  custom: True
               name: _NotIterable
               module: typing
               package:
            *  custom: True
               name: _GenericAlias
               module: typing
               package:
            *  custom: True
               name: _BaseGenericAlias
               module: typing
               package:
            *  custom: True
               name: _Final
               module: typing
               package:
            *  custom: False
               name: object
               module: builtins
               package:
        """,
        )

    @pytest.mark.skipif(sys.version_info < (3, 11), reason="requires python3.11 or higher")
    it "works on a typing union", type_cache: strcs.TypeCache:
        provided = tp.Union[int, str]
        disassembled = Type.create(provided, expect=types.UnionType, cache=type_cache)
        self.assertDisplay(
            disassembled,
            """
          x Union optional
          2 Union length
          ✓ Union:
            *  x Union optional
               x Union
               x Annotated
               0 typevars ()
               x Typevars
               x Optional
               2 MRO length
               ✓ Origin MRO:
                 *  custom: False
                    name: str
                    module: builtins
                    package:
                 *  custom: False
                    name: object
                    module: builtins
                    package:
            *  x Union optional
               x Union
               x Annotated
               0 typevars ()
               x Typevars
               x Optional
               2 MRO length
               ✓ Origin MRO:
                 *  custom: False
                    name: int
                    module: builtins
                    package:
                 *  custom: False
                    name: object
                    module: builtins
                    package:
          x Annotated
          0 typevars ()
          x Typevars
          x Optional
          6 MRO length
          ✓ Origin MRO:
            *  custom: True
               name: _UnionGenericAlias
               module: typing
               package:
            *  custom: True
               name: _NotIterable
               module: typing
               package:
            *  custom: True
               name: _GenericAlias
               module: typing
               package:
            *  custom: True
               name: _BaseGenericAlias
               module: typing
               package:
            *  custom: True
               name: _Final
               module: typing
               package:
            *  custom: False
               name: object
               module: builtins
               package:
        """,
        )

    it "works on an optional union", type_cache: strcs.TypeCache:
        provided = int | str | None
        disassembled = Type.create(provided, expect=types.UnionType, cache=type_cache)
        self.assertDisplay(
            disassembled,
            """
          ✓ Union optional
          2 Union length
          ✓ Union:
            *  x Union optional
               x Union
               x Annotated
               0 typevars ()
               x Typevars
               x Optional
               2 MRO length
               ✓ Origin MRO:
                 *  custom: False
                    name: str
                    module: builtins
                    package:
                 *  custom: False
                    name: object
                    module: builtins
                    package:
            *  x Union optional
               x Union
               x Annotated
               0 typevars ()
               x Typevars
               x Optional
               2 MRO length
               ✓ Origin MRO:
                 *  custom: False
                    name: int
                    module: builtins
                    package:
                 *  custom: False
                    name: object
                    module: builtins
                    package:
          x Annotated
          0 typevars ()
          x Typevars
          ✓ Optional
          2 MRO length
          ✓ Origin MRO:
            *  custom: True
               name: UnionType
               module: types
               package:
            *  custom: False
               name: object
               module: builtins
               package:
        """,
        )

    it "works on optional simple type", type_cache: strcs.TypeCache:
        provided = int | None
        disassembled = Type.create(provided, expect=int, cache=type_cache)
        self.assertDisplay(
            disassembled,
            """
          x Union optional
          x Union
          x Annotated
          0 typevars ()
          x Typevars
          ✓ Optional
          2 MRO length
          ✓ Origin MRO:
            *  custom: False
               name: int
               module: builtins
               package:
            *  custom: False
               name: object
               module: builtins
               package:
        """,
        )

    it "works on annotated simple type", type_cache: strcs.TypeCache:
        anno = "hello"
        provided = tp.Annotated[int, anno]
        disassembled = Type.create(provided, expect=int, cache=type_cache)
        self.assertDisplay(
            disassembled,
            """
          x Union optional
          x Union
          ✓ Annotated
          0 typevars ()
          x Typevars
          x Optional
          2 MRO length
          ✓ Origin MRO:
            *  custom: False
               name: int
               module: builtins
               package:
            *  custom: False
               name: object
               module: builtins
               package:
        """,
        )

    it "works on optional annotated simple type", type_cache: strcs.TypeCache:
        anno = "hello"
        provided = tp.Annotated[tp.Optional[int], anno]
        disassembled = Type.create(provided, expect=int, cache=type_cache)
        self.assertDisplay(
            disassembled,
            """
          x Union optional
          x Union
          ✓ Annotated
          0 typevars ()
          x Typevars
          ✓ Optional
          2 MRO length
          ✓ Origin MRO:
            *  custom: False
               name: int
               module: builtins
               package:
            *  custom: False
               name: object
               module: builtins
               package:
        """,
        )

    it "works on builtin container to simple type", type_cache: strcs.TypeCache:
        provided = list[int]
        disassembled = Type.create(provided, expect=list, cache=type_cache)
        self.assertDisplay(
            disassembled,
            """
          x Union optional
          x Union
          x Annotated
          1 typevars (True,)
          ✓ Typevars:
            *  x Union optional
               x Union
               x Annotated
               0 typevars ()
               x Typevars
               x Optional
               2 MRO length
               ✓ Origin MRO:
                 *  custom: False
                    name: int
                    module: builtins
                    package:
                 *  custom: False
                    name: object
                    module: builtins
                    package:
          x Optional
          2 MRO length
          ✓ Origin MRO:
            *  custom: False
               name: list
               module: builtins
               package:
            *  custom: False
               name: object
               module: builtins
               package:
        """,
        )

    it "works on optional builtin container to simple type", type_cache: strcs.TypeCache:
        provided = list[int] | None
        disassembled = Type.create(provided, expect=list, cache=type_cache)
        self.assertDisplay(
            disassembled,
            """
          x Union optional
          x Union
          x Annotated
          1 typevars (True,)
          ✓ Typevars:
            *  x Union optional
               x Union
               x Annotated
               0 typevars ()
               x Typevars
               x Optional
               2 MRO length
               ✓ Origin MRO:
                 *  custom: False
                    name: int
                    module: builtins
                    package:
                 *  custom: False
                    name: object
                    module: builtins
                    package:
          ✓ Optional
          2 MRO length
          ✓ Origin MRO:
            *  custom: False
               name: list
               module: builtins
               package:
            *  custom: False
               name: object
               module: builtins
               package:
        """,
        )

    it "works on builtin container to multiple simple types", type_cache: strcs.TypeCache:
        provided = dict[str, int]
        disassembled = Type.create(provided, expect=dict, cache=type_cache)
        self.assertDisplay(
            disassembled,
            """
          x Union optional
          x Union
          x Annotated
          2 typevars (True, True)
          ✓ Typevars:
            *  x Union optional
               x Union
               x Annotated
               0 typevars ()
               x Typevars
               x Optional
               2 MRO length
               ✓ Origin MRO:
                 *  custom: False
                    name: str
                    module: builtins
                    package:
                 *  custom: False
                    name: object
                    module: builtins
                    package:
            *  x Union optional
               x Union
               x Annotated
               0 typevars ()
               x Typevars
               x Optional
               2 MRO length
               ✓ Origin MRO:
                 *  custom: False
                    name: int
                    module: builtins
                    package:
                 *  custom: False
                    name: object
                    module: builtins
                    package:
          x Optional
          2 MRO length
          ✓ Origin MRO:
            *  custom: False
               name: dict
               module: builtins
               package:
            *  custom: False
               name: object
               module: builtins
               package:
        """,
        )

    it "works on optional builtin container to multiple simple types", type_cache: strcs.TypeCache:
        provided = tp.Optional[dict[str, int]]
        disassembled = Type.create(provided, expect=dict, cache=type_cache)
        self.assertDisplay(
            disassembled,
            """
          x Union optional
          x Union
          x Annotated
          2 typevars (True, True)
          ✓ Typevars:
            *  x Union optional
               x Union
               x Annotated
               0 typevars ()
               x Typevars
               x Optional
               2 MRO length
               ✓ Origin MRO:
                 *  custom: False
                    name: str
                    module: builtins
                    package:
                 *  custom: False
                    name: object
                    module: builtins
                    package:
            *  x Union optional
               x Union
               x Annotated
               0 typevars ()
               x Typevars
               x Optional
               2 MRO length
               ✓ Origin MRO:
                 *  custom: False
                    name: int
                    module: builtins
                    package:
                 *  custom: False
                    name: object
                    module: builtins
                    package:
          ✓ Optional
          2 MRO length
          ✓ Origin MRO:
            *  custom: False
               name: dict
               module: builtins
               package:
            *  custom: False
               name: object
               module: builtins
               package:
        """,
        )

    it "works on annotated optional builtin container to multiple simple types", type_cache: strcs.TypeCache:
        anno = "stuff"
        provided = tp.Annotated[tp.Optional[dict[str, int]], anno]
        disassembled = Type.create(provided, expect=dict, cache=type_cache)
        self.assertDisplay(
            disassembled,
            """
          x Union optional
          x Union
          ✓ Annotated
          2 typevars (True, True)
          ✓ Typevars:
            *  x Union optional
               x Union
               x Annotated
               0 typevars ()
               x Typevars
               x Optional
               2 MRO length
               ✓ Origin MRO:
                 *  custom: False
                    name: str
                    module: builtins
                    package:
                 *  custom: False
                    name: object
                    module: builtins
                    package:
            *  x Union optional
               x Union
               x Annotated
               0 typevars ()
               x Typevars
               x Optional
               2 MRO length
               ✓ Origin MRO:
                 *  custom: False
                    name: int
                    module: builtins
                    package:
                 *  custom: False
                    name: object
                    module: builtins
                    package:
          ✓ Optional
          2 MRO length
          ✓ Origin MRO:
            *  custom: False
               name: dict
               module: builtins
               package:
            *  custom: False
               name: object
               module: builtins
               package:
        """,
        )

    it "works on optional annotated builtin container to multiple simple types", type_cache: strcs.TypeCache:
        anno = "stuff"
        provided = tp.Optional[tp.Annotated[dict[str, int], anno]]
        disassembled = Type.create(provided, expect=dict, cache=type_cache)
        self.assertDisplay(
            disassembled,
            """
          x Union optional
          x Union
          ✓ Annotated
          2 typevars (True, True)
          ✓ Typevars:
            *  x Union optional
               x Union
               x Annotated
               0 typevars ()
               x Typevars
               x Optional
               2 MRO length
               ✓ Origin MRO:
                 *  custom: False
                    name: str
                    module: builtins
                    package:
                 *  custom: False
                    name: object
                    module: builtins
                    package:
            *  x Union optional
               x Union
               x Annotated
               0 typevars ()
               x Typevars
               x Optional
               2 MRO length
               ✓ Origin MRO:
                 *  custom: False
                    name: int
                    module: builtins
                    package:
                 *  custom: False
                    name: object
                    module: builtins
                    package:
          ✓ Optional
          2 MRO length
          ✓ Origin MRO:
            *  custom: False
               name: dict
               module: builtins
               package:
            *  custom: False
               name: object
               module: builtins
               package:
        """,
        )

    it "works on an attrs class", type_cache: strcs.TypeCache:

        @attrs.define
        class Thing:
            one: int
            two: str

        provided = Thing
        disassembled = Type.create(provided, expect=Thing, cache=type_cache)
        self.assertDisplay(
            disassembled,
            """
          x Union optional
          x Union
          x Annotated
          0 typevars ()
          x Typevars
          x Optional
          2 MRO length
          ✓ Origin MRO:
            *  custom: True
               name: Thing
               module: tests.disassemble.test_score_display
               package:
            *  custom: False
               name: object
               module: builtins
               package:
        """,
        )

    it "works on an dataclasses class", type_cache: strcs.TypeCache:

        @dataclasses.dataclass
        class Thing:
            one: int
            two: str

        provided = Thing
        disassembled = Type.create(provided, expect=Thing, cache=type_cache)
        self.assertDisplay(
            disassembled,
            """
          x Union optional
          x Union
          x Annotated
          0 typevars ()
          x Typevars
          x Optional
          2 MRO length
          ✓ Origin MRO:
            *  custom: True
               name: Thing
               module: tests.disassemble.test_score_display
               package:
            *  custom: False
               name: object
               module: builtins
               package:
        """,
        )

    it "works on a normal class", type_cache: strcs.TypeCache:

        class Thing:
            def __init__(self, one: int, two: str):
                self.one = one
                self.two = two

        provided = Thing
        disassembled = Type.create(provided, expect=Thing, cache=type_cache)
        self.assertDisplay(
            disassembled,
            """
          x Union optional
          x Union
          x Annotated
          0 typevars ()
          x Typevars
          x Optional
          2 MRO length
          ✓ Origin MRO:
            *  custom: True
               name: Thing
               module: tests.disassemble.test_score_display
               package:
            *  custom: False
               name: object
               module: builtins
               package:
        """,
        )

    it "works on inherited generic container", type_cache: strcs.TypeCache:

        class D(dict[str, int]):
            pass

        provided = D
        disassembled = Type.create(provided, expect=D, cache=type_cache)
        self.assertDisplay(
            disassembled,
            """
          x Union optional
          x Union
          x Annotated
          2 typevars (True, True)
          ✓ Typevars:
            *  x Union optional
               x Union
               x Annotated
               0 typevars ()
               x Typevars
               x Optional
               2 MRO length
               ✓ Origin MRO:
                 *  custom: False
                    name: str
                    module: builtins
                    package:
                 *  custom: False
                    name: object
                    module: builtins
                    package:
            *  x Union optional
               x Union
               x Annotated
               0 typevars ()
               x Typevars
               x Optional
               2 MRO length
               ✓ Origin MRO:
                 *  custom: False
                    name: int
                    module: builtins
                    package:
                 *  custom: False
                    name: object
                    module: builtins
                    package:
          x Optional
          3 MRO length
          ✓ Origin MRO:
            *  custom: True
               name: D
               module: tests.disassemble.test_score_display
               package:
            *  custom: False
               name: dict
               module: builtins
               package:
            *  custom: False
               name: object
               module: builtins
               package:
        """,
        )

    it "works on class with complicated hierarchy", type_cache: strcs.TypeCache:

        class Thing(tp.Generic[T, U]):
            def __init__(self, one: int, two: str):
                self.one = one
                self.two = two

        class Stuff(tp.Generic[T], Thing[int, T]):
            def __init__(self, one: int, two: str, three: bool):
                super().__init__(one, two)
                self.three = three

        class Blah(tp.Generic[U], Stuff[str]):
            pass

        class Meh(Blah[bool]):
            pass

        class Tree(Meh):
            def __init__(self, four: str):
                super().__init__(1, "two", True)
                self.four = four

        provided = Tree
        disassembled = Type.create(provided, expect=Tree, cache=type_cache)
        self.assertDisplay(
            disassembled,
            """
          x Union optional
          x Union
          x Annotated
          3 typevars (True, True, True)
          ✓ Typevars:
            *  x Union optional
               x Union
               x Annotated
               0 typevars ()
               x Typevars
               x Optional
               3 MRO length
               ✓ Origin MRO:
                 *  custom: False
                    name: bool
                    module: builtins
                    package:
                 *  custom: False
                    name: int
                    module: builtins
                    package:
                 *  custom: False
                    name: object
                    module: builtins
                    package:
            *  x Union optional
               x Union
               x Annotated
               0 typevars ()
               x Typevars
               x Optional
               2 MRO length
               ✓ Origin MRO:
                 *  custom: False
                    name: int
                    module: builtins
                    package:
                 *  custom: False
                    name: object
                    module: builtins
                    package:
            *  x Union optional
               x Union
               x Annotated
               0 typevars ()
               x Typevars
               x Optional
               2 MRO length
               ✓ Origin MRO:
                 *  custom: False
                    name: str
                    module: builtins
                    package:
                 *  custom: False
                    name: object
                    module: builtins
                    package:
          x Optional
          7 MRO length
          ✓ Origin MRO:
            *  custom: True
               name: Tree
               module: tests.disassemble.test_score_display
               package:
            *  custom: True
               name: Meh
               module: tests.disassemble.test_score_display
               package:
            *  custom: True
               name: Blah
               module: tests.disassemble.test_score_display
               package:
            *  custom: True
               name: Stuff
               module: tests.disassemble.test_score_display
               package:
            *  custom: True
               name: Thing
               module: tests.disassemble.test_score_display
               package:
            *  custom: True
               name: Generic
               module: typing
               package:
            *  custom: False
               name: object
               module: builtins
               package:
        """,
        )

    it "works on an annotated class", type_cache: strcs.TypeCache:

        @attrs.define
        class Thing:
            one: int
            two: str

        anno = "blah"

        provided = tp.Annotated[Thing, anno]
        disassembled = Type.create(provided, expect=Thing, cache=type_cache)
        self.assertDisplay(
            disassembled,
            """
          x Union optional
          x Union
          ✓ Annotated
          0 typevars ()
          x Typevars
          x Optional
          2 MRO length
          ✓ Origin MRO:
            *  custom: True
               name: Thing
               module: tests.disassemble.test_score_display
               package:
            *  custom: False
               name: object
               module: builtins
               package:
        """,
        )

    it "works on an optional annotated class", type_cache: strcs.TypeCache:

        @dataclasses.dataclass
        class Thing:
            one: int
            two: str

        anno = "blah"

        provided = tp.Annotated[tp.Optional[Thing], anno]
        disassembled = Type.create(provided, expect=Thing, cache=type_cache)
        self.assertDisplay(
            disassembled,
            """
          x Union optional
          x Union
          ✓ Annotated
          0 typevars ()
          x Typevars
          ✓ Optional
          2 MRO length
          ✓ Origin MRO:
            *  custom: True
               name: Thing
               module: tests.disassemble.test_score_display
               package:
            *  custom: False
               name: object
               module: builtins
               package:
        """,
        )

    it "works on an optional annotated generic class", type_cache: strcs.TypeCache:

        @dataclasses.dataclass
        class Thing(tp.Generic[T, U]):
            one: T
            two: U

        anno = "blah"

        provided = tp.Annotated[tp.Optional[Thing[int, str]], anno]
        disassembled = Type.create(provided, expect=Thing, cache=type_cache)
        self.assertDisplay(
            disassembled,
            """
          x Union optional
          x Union
          ✓ Annotated
          2 typevars (True, True)
          ✓ Typevars:
            *  x Union optional
               x Union
               x Annotated
               0 typevars ()
               x Typevars
               x Optional
               2 MRO length
               ✓ Origin MRO:
                 *  custom: False
                    name: int
                    module: builtins
                    package:
                 *  custom: False
                    name: object
                    module: builtins
                    package:
            *  x Union optional
               x Union
               x Annotated
               0 typevars ()
               x Typevars
               x Optional
               2 MRO length
               ✓ Origin MRO:
                 *  custom: False
                    name: str
                    module: builtins
                    package:
                 *  custom: False
                    name: object
                    module: builtins
                    package:
          ✓ Optional
          3 MRO length
          ✓ Origin MRO:
            *  custom: True
               name: Thing
               module: tests.disassemble.test_score_display
               package:
            *  custom: True
               name: Generic
               module: typing
               package:
            *  custom: False
               name: object
               module: builtins
               package:
        """,
        )

    it "works on an optional annotated generic class without concrete types", type_cache: strcs.TypeCache:

        @attrs.define
        class Thing(tp.Generic[T, U]):
            one: T
            two: U

        anno = "blah"

        provided = tp.Annotated[tp.Optional[Thing], anno]
        disassembled = Type.create(provided, expect=Thing, cache=type_cache)
        self.assertDisplay(
            disassembled,
            """
          x Union optional
          x Union
          ✓ Annotated
          2 typevars (False, False)
          ✓ Typevars:
            *  x Union optional
               x Union
               x Annotated
               0 typevars ()
               x Typevars
               x Optional
               0 MRO length
               x Origin MRO
            *  x Union optional
               x Union
               x Annotated
               0 typevars ()
               x Typevars
               x Optional
               0 MRO length
               x Origin MRO
          ✓ Optional
          3 MRO length
          ✓ Origin MRO:
            *  custom: True
               name: Thing
               module: tests.disassemble.test_score_display
               package:
            *  custom: True
               name: Generic
               module: typing
               package:
            *  custom: False
               name: object
               module: builtins
               package:
        """,
        )

    it "works on an optional annotated generic class with concrete types", type_cache: strcs.TypeCache:

        @attrs.define
        class Thing(tp.Generic[T, U]):
            one: T
            two: U

        anno = "blah"

        provided = tp.Annotated[tp.Optional[Thing[int, str]], anno]
        disassembled = Type.create(provided, expect=Thing, cache=type_cache)
        self.assertDisplay(
            disassembled,
            """
          x Union optional
          x Union
          ✓ Annotated
          2 typevars (True, True)
          ✓ Typevars:
            *  x Union optional
               x Union
               x Annotated
               0 typevars ()
               x Typevars
               x Optional
               2 MRO length
               ✓ Origin MRO:
                 *  custom: False
                    name: int
                    module: builtins
                    package:
                 *  custom: False
                    name: object
                    module: builtins
                    package:
            *  x Union optional
               x Union
               x Annotated
               0 typevars ()
               x Typevars
               x Optional
               2 MRO length
               ✓ Origin MRO:
                 *  custom: False
                    name: str
                    module: builtins
                    package:
                 *  custom: False
                    name: object
                    module: builtins
                    package:
          ✓ Optional
          3 MRO length
          ✓ Origin MRO:
            *  custom: True
               name: Thing
               module: tests.disassemble.test_score_display
               package:
            *  custom: True
               name: Generic
               module: typing
               package:
            *  custom: False
               name: object
               module: builtins
               package:
        """,
        )
