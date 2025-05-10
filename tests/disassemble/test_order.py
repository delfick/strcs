import random
import typing as tp

import pytest

import strcs

Disassembler = strcs.disassemble.Disassembler


class Sorter:
    @classmethod
    def make_fixture(cls) -> tp.Callable[[Disassembler], "Sorter"]:
        @pytest.fixture
        def fixture(Dis: Disassembler) -> Sorter:
            return cls(Dis)

        return fixture

    def __init__(self, Dis: Disassembler):
        self.Dis = Dis

    def make_type(self, original: object | type) -> strcs.Type:
        return self.Dis(original)

    def assert_reverse_order(self, *to_sort: object) -> None:
        types: list[strcs.Type] = [self.make_type(original) for original in to_sort]
        want = list(types)

        for _ in range(5):
            shuffling = list(types)
            random.shuffle(shuffling)

            srtd = list(sorted(shuffling, reverse=True))
            if srtd != want:
                # for part in srtd:
                #     print(part.for_display())
                #     print(part.score.for_display(indent="  "))
                #     print()

                # print("\n======\n")

                # for part in srtd:
                #     print(part.for_display())

                assert srtd == want


sorter = Sorter.make_fixture()


class TestOrderingTypes:
    def test_it_orders_basic_types_by_reverse_alphabetical_name(self, sorter: Sorter):
        sorter.assert_reverse_order(
            str,
            int,
            dict,
        )

    def test_it_orders_bool_before_int_cause_it_has_an_mro_of_3_vs_2(self, sorter: Sorter):
        sorter.assert_reverse_order(
            bool,
            int,
        )

    def test_it_orders_optionals_at_the_start_of_the_list(self, sorter: Sorter):
        sorter.assert_reverse_order(
            bool | None,
            int | None,
            dict | None,
            bool,
            int,
            dict,
        )

    def test_it_orders_annotated_at_the_start_of_the_list(self, sorter: Sorter):
        sorter.assert_reverse_order(
            tp.Annotated[bool | None, 1],
            tp.Annotated[int | None, 1],
            tp.Annotated[dict | None, 1],
            tp.Annotated[bool, 1],
            tp.Annotated[int, 1],
            tp.Annotated[dict, 1],
            bool | None,
            int | None,
            dict | None,
            bool,
            int,
            dict,
        )

    def test_it_orders_class_before_builtin(self, sorter: Sorter):
        class Stuff:
            pass

        sorter.assert_reverse_order(
            Stuff,
            int,
        )

    def test_it_orders_unions_reverse_alphabetically(self, sorter: Sorter):
        sorter.assert_reverse_order(
            bool | str,
            bool | int,
            dict | bool,
            int | str,
        )

    def test_it_prefers_annotations(self, sorter: Sorter):
        sorter.assert_reverse_order(
            tp.Annotated[int | str, False],
            bool | tp.Annotated[int, True],
            bool | str,
        )

    def test_it_orders_longer_unions_before_shorter_unions_and_optional_unions_before_other_unions(
        self, sorter: Sorter
    ):
        sorter.assert_reverse_order(
            bool | str | None,
            int | str | dict,
            bool | str,
            int | str,
            # int | None isn't a union, cause it's just optional!
            int | None,
            int,
        )

    def test_it_orders_unions_before_non_unions(self, sorter: Sorter):
        class Thing:
            pass

        class Stuff(Thing):
            pass

        sorter.assert_reverse_order(
            tp.Annotated[Stuff | int | None, True],
            tp.Annotated[str | int | None, True],
            str | int | None,
            bool | str | Thing | Stuff,
            str | int | Thing,
            bool | str,
            str | int,
            Stuff,
            bool,
            int,
        )

    def test_it_orders_classes_by_length_of_the_mro_with_longer_mro_first(self, sorter: Sorter):
        class One:
            pass

        class Two(One):
            pass

        class Three(Two):
            pass

        class Une:
            pass

        class Deux(Une):
            pass

        class Trois(Deux):
            pass

        sorter.assert_reverse_order(
            Trois,
            Three,
            Two,
            Deux,
            Une,
            One,
        )

    def test_it_orders_generic_classes(self, sorter: Sorter):
        T = tp.TypeVar("T")
        U = tp.TypeVar("U")

        class One(tp.Generic[T]):
            pass

        class Two(One[str]):
            pass

        class Three(One[int]):
            pass

        class Four(One):
            pass

        class Une:
            pass

        class Deux(Une):
            pass

        class Ichi(tp.Generic[T, U]):
            pass

        class Ni(Ichi[str, int]):
            pass

        class San(Ichi[int, str]):
            pass

        class Shi(tp.Generic[T], Ichi[str, T]):
            pass

        class Go(Shi[int]):
            pass

        sorter.assert_reverse_order(
            # Ichi[str, int] + 1mro
            Go,
            # Ichi[str, int] + 1mro
            Ni,
            # Ichi[int, str] + 1mro
            San,
            # Ichi[str, T] + 1mro
            Shi,
            # One[str] + 1mro
            Two,
            # One[int] + 1mro
            Three,
            # One + 1mro
            Four,
            # Ichi[str, int]
            Ichi[str, int],
            # Ichi[T, U]
            Ichi,
            # One[bool]
            One[bool],
            # One[int]
            One[int],
            # One
            One,
            # Deux
            Deux,
            # Une
            Une,
        )

    def test_it_doesnt_reorder_typevars(self, sorter: Sorter):
        T = tp.TypeVar("T")
        U = tp.TypeVar("U")

        class One(tp.Generic[T, U]):
            pass

        class Two(One[str, int]):
            pass

        class Three(One[int, str]):
            pass

        class Four(tp.Generic[T], One[bool, T]):
            pass

        class Five(tp.Generic[T], One[dict, T]):
            pass

        class Six:
            pass

        sorter.assert_reverse_order(
            # One[bool, tp.Annotated[dict]] + 1mro
            Four[tp.Annotated[dict, False]],
            # One[bool, bool] + 1mro
            Four[bool],
            # One[bool, dict] + 1mro
            Four[dict],
            # One[int, str] + 1mro
            Two,
            # One[int, str] + 1mro
            Three,
            # One[dict, tp.Annotated[dict]] + 1mro
            Five[tp.Annotated[dict, False]],
            # One[dict, bool] + 1mro
            Five[bool],
            # One[dict, dict] + 1mro
            Five[dict],
            # One[bool, T] + 1mro
            Four,
            One[tp.Annotated[bool, False], int],
            One[tp.Annotated[int, False], int],
            One[Six | None, int],
            One[Six, int],
            One[bool, tp.Annotated[bool, False]],
            One[bool, tp.Annotated[dict, False]],
            One[bool, bool],
            One[bool, dict],
            One[dict, Six | None],
            One[dict, Six],
            Six,
            bool,
            str,
            int,
            dict,
        )
