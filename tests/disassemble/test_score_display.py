import dataclasses
import itertools
import sys
import textwrap
import typing as tp

import attrs
import pytest

import strcs
from strcs import Type

Disassembler = strcs.disassemble.Disassembler


T = tp.TypeVar("T")
U = tp.TypeVar("U")


class TestType:
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

    def test_it_works_on_None(self, Dis: Disassembler):
        provided = None
        disassembled = Dis(provided)
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

    def test_it_doesnt_overcome_python_limitations_with_annotating_None_and_thinks_we_annotated_type_of_None(
        self, Dis: Disassembler
    ):
        provided = tp.Annotated[None, 1]
        disassembled = Dis(provided)
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

    def test_it_works_on_simple_type(self, Dis: Disassembler):
        provided = int
        disassembled = Dis(provided)
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

    def test_it_works_on_a_union(self, Dis: Disassembler):
        provided = int | str
        disassembled = Dis(provided)
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
    def test_it_works_on_a_complicated_union(self, Dis: Disassembler):
        provided = tp.Union[
            tp.Annotated[list[int], "str"], tp.Annotated[int | str | None, '"hello']
        ]
        disassembled = Dis(provided)
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
    def test_it_works_on_a_typing_union(self, Dis: Disassembler):
        provided = tp.Union[int, str]
        disassembled = Dis(provided)
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

    def test_it_works_on_an_optional_union(self, Dis: Disassembler):
        provided = int | str | None
        disassembled = Dis(provided)
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

    def test_it_works_on_optional_simple_type(self, Dis: Disassembler):
        provided = int | None
        disassembled = Dis(provided)
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

    def test_it_works_on_annotated_simple_type(self, Dis: Disassembler):
        anno = "hello"
        provided = tp.Annotated[int, anno]
        disassembled = Dis(provided)
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

    def test_it_works_on_optional_annotated_simple_type(self, Dis: Disassembler):
        anno = "hello"
        provided = tp.Annotated[tp.Optional[int], anno]
        disassembled = Dis(provided)
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

    def test_it_works_on_builtin_container_to_simple_type(self, Dis: Disassembler):
        provided = list[int]
        disassembled = Dis(provided)
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

    def test_it_works_on_optional_builtin_container_to_simple_type(self, Dis: Disassembler):
        provided = list[int] | None
        disassembled = Dis(provided)
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

    def test_it_works_on_builtin_container_to_multiple_simple_types(self, Dis: Disassembler):
        provided = dict[str, int]
        disassembled = Dis(provided)
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

    def test_it_works_on_optional_builtin_container_to_multiple_simple_types(
        self, Dis: Disassembler
    ):
        provided = tp.Optional[dict[str, int]]
        disassembled = Dis(provided)
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

    def test_it_works_on_annotated_optional_builtin_container_to_multiple_simple_types(
        self, Dis: Disassembler
    ):
        anno = "stuff"
        provided = tp.Annotated[tp.Optional[dict[str, int]], anno]
        disassembled = Dis(provided)
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

    def test_it_works_on_optional_annotated_builtin_container_to_multiple_simple_types(
        self, Dis: Disassembler
    ):
        anno = "stuff"
        provided = tp.Optional[tp.Annotated[dict[str, int], anno]]
        disassembled = Dis(provided)
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

    def test_it_works_on_an_attrs_class(self, Dis: Disassembler):
        @attrs.define
        class Thing:
            one: int
            two: str

        provided = Thing
        disassembled = Dis(provided)
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

    def test_it_works_on_an_dataclasses_class(self, Dis: Disassembler):
        @dataclasses.dataclass
        class Thing:
            one: int
            two: str

        provided = Thing
        disassembled = Dis(provided)
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

    def test_it_works_on_a_normal_class(self, Dis: Disassembler):
        class Thing:
            def __init__(self, one: int, two: str):
                self.one = one
                self.two = two

        provided = Thing
        disassembled = Dis(provided)
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

    def test_it_works_on_inherited_generic_container(self, Dis: Disassembler):
        class D(dict[str, int]):
            pass

        provided = D
        disassembled = Dis(provided)
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

    def test_it_works_on_class_with_complicated_hierarchy(self, Dis: Disassembler):
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
        disassembled = Dis(provided)
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

    def test_it_works_on_an_annotated_class(self, Dis: Disassembler):
        @attrs.define
        class Thing:
            one: int
            two: str

        anno = "blah"

        provided = tp.Annotated[Thing, anno]
        disassembled = Dis(provided)
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

    def test_it_works_on_an_optional_annotated_class(self, Dis: Disassembler):
        @dataclasses.dataclass
        class Thing:
            one: int
            two: str

        anno = "blah"

        provided = tp.Annotated[tp.Optional[Thing], anno]
        disassembled = Dis(provided)
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

    def test_it_works_on_an_optional_annotated_generic_class(self, Dis: Disassembler):
        @dataclasses.dataclass
        class Thing(tp.Generic[T, U]):
            one: T
            two: U

        anno = "blah"

        provided = tp.Annotated[tp.Optional[Thing[int, str]], anno]
        disassembled = Dis(provided)
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

    def test_it_works_on_an_optional_annotated_generic_class_without_concrete_types(
        self, Dis: Disassembler
    ):
        @attrs.define
        class Thing(tp.Generic[T, U]):
            one: T
            two: U

        anno = "blah"

        provided = tp.Annotated[tp.Optional[Thing], anno]
        disassembled = Dis(provided)
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

    def test_it_works_on_an_optional_annotated_generic_class_with_concrete_types(
        self, Dis: Disassembler
    ):
        @attrs.define
        class Thing(tp.Generic[T, U]):
            one: T
            two: U

        anno = "blah"

        provided = tp.Annotated[tp.Optional[Thing[int, str]], anno]
        disassembled = Dis(provided)
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

    def test_it_works_with_NewType_generic_params(self, Dis: Disassembler):
        @attrs.define
        class Thing(tp.Generic[T, U]):
            one: T
            two: U

        One = tp.NewType("One", int)
        Two = tp.NewType("Two", int)

        provided = Thing[One, Two]
        disassembled = Dis(provided)
        self.assertDisplay(
            disassembled,
            """
            x Union optional
            x Union
            x Annotated
            2 typevars (True, True)
            ✓ Typevars:
              *  ✓ type alias: One
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
              *  ✓ type alias: Two
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
            x Optional
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

    def test_it_works_with_NewType_class(self, Dis: Disassembler):
        class Thing(str):
            pass

        ThingAlias = tp.NewType("ThingAlias", Thing)

        provided = ThingAlias
        disassembled = Dis(provided)
        self.assertDisplay(
            disassembled,
            """
            ✓ type alias: ThingAlias
            x Union optional
            x Union
            x Annotated
            0 typevars ()
            x Typevars
            x Optional
            3 MRO length
            ✓ Origin MRO:
              *  custom: True
                 name: Thing
                 module: tests.disassemble.test_score_display
                 package:
              *  custom: False
                 name: str
                 module: builtins
                 package:
              *  custom: False
                 name: object
                 module: builtins
                 package:
            """,
        )
