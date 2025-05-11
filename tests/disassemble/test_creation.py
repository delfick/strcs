from typing import Annotated

import attrs
import cattrs
import pytest

import strcs
from strcs.disassemble import fill, instantiate

Disassembler = strcs.disassemble.Disassembler


class TestFill:
    def test_it_turns_NotSpecified_into_an_empty_dictionary(self, Dis: Disassembler):
        class Thing:
            pass

        want = Dis(Thing)

        assert fill(want, strcs.NotSpecified) == {}

    def test_it_complains_if_res_is_not_a_mapping(self, Dis: Disassembler) -> None:
        class Thing:
            pass

        want = Dis(Thing)

        res: object
        for res in (1, 0, True, False, [], [1], set(), lambda: 1, Thing, Thing()):
            with pytest.raises(ValueError, match="Can only fill mappings"):
                fill(want, res)

    def test_it_fills_in_annotated_or_other_objects_with_NotSpecified(self, Dis: Disassembler):
        class Two:
            pass

        @attrs.define
        class Thing:
            one: Annotated[int, 1]
            two: Two
            three: bool
            four: int

        res = {"four": 1}
        want = Dis(Thing)
        assert fill(want, res) == {"one": strcs.NotSpecified, "two": strcs.NotSpecified, "four": 1}

    def test_it_doesnt_override_fields(self, Dis: Disassembler):
        class Two:
            pass

        @attrs.define
        class Thing:
            one: Annotated[int, 1]
            two: Two
            three: bool
            four: int

        two = Two()
        res = {"one": 3, "two": two, "three": True, "four": 1}
        want = Dis(Thing)
        assert fill(want, res) == {"one": 3, "two": two, "three": True, "four": 1}


class TestInstantiate:
    def test_it_returns_None_if_the_result_is_optional_and_res_is_None(self, Dis: Disassembler):
        class Thing:
            pass

        want = Dis(Thing | None)
        assert instantiate(want, None, cattrs.Converter()) is None

    def test_it_returns_None_if_want_None_and_are_None(self, Dis: Disassembler):
        want = Dis(None)
        assert instantiate(want, None, cattrs.Converter()) is None

    def test_it_complains_if_res_is_None_and_we_arent_optional_or_None(self, Dis: Disassembler):
        class Thing:
            pass

        want = Dis(Thing)
        with pytest.raises(ValueError, match="Can't instantiate object with None"):
            instantiate(want, None, cattrs.Converter())


class TestCreation:
    def test_it_deals_with_private_fields_in_an_attrs_class(self) -> None:
        reg = strcs.CreateRegister()

        @attrs.define
        class Thing:
            one: int
            _two: int

        thing = Thing(one=1, two=20)
        assert thing.one == 1
        assert thing._two == 20

        thing2 = reg.create(Thing, {"one": 1, "two": 20})
        assert thing2.one == 1
        assert thing2._two == 20

    def test_it_deals_with_private_fields_in_not_attrs_class(self):
        reg = strcs.CreateRegister()

        class Thing:
            def __init__(self, one: int, _two: int):
                self.one = one
                self._two = _two

        thing = Thing(one=1, _two=20)
        assert thing.one == 1
        assert thing._two == 20

        thing2 = reg.create(Thing, {"one": 1, "_two": 20})
        assert thing2.one == 1
        assert thing2._two == 20

    def test_it_invokes_creators_for_annotated_fields(self):
        reg = strcs.CreateRegister()

        def doubler(val: object, /) -> int:
            assert isinstance(val, int)
            return val * 2

        class Thing:
            def __init__(self, one: Annotated[int, strcs.Ann(creator=doubler)]):
                self.one = one

        thing = Thing(one=1)
        assert thing.one == 1

        thing2 = reg.create(Thing, {"one": 1})
        assert thing2.one == 2

    def test_it_invokes_creators_for_annotated_fields_even_if_not_provided(self):
        reg = strcs.CreateRegister()

        def doubler(val: object, /) -> int:
            assert val is strcs.NotSpecified
            return 200

        class Thing:
            def __init__(self, one: Annotated[int, strcs.Ann(creator=doubler)]):
                self.one = one

        with pytest.raises(TypeError):
            Thing()  # type: ignore[call-arg]

        thing2 = reg.create(Thing)
        assert thing2.one == 200

    def test_it_invokes_creators_for_other_classes_even_if_not_provided(self) -> None:
        reg = strcs.CreateRegister()

        @attrs.define
        class Two:
            three: bool = True

        class Thing:
            def __init__(self, two: Two):
                self.two = two

        with pytest.raises(TypeError):
            Thing()  # type: ignore[call-arg]

        thing2 = reg.create(Thing)
        assert thing2.two == Two(three=True)

    def test_it_doesnt_care_for_fields_on_parents_not_part_of_the_child(self, Dis: Disassembler):
        reg = strcs.CreateRegister()

        class One:
            def __init__(self, one: int, two: int):
                self.one = one
                self.two = two

        class Two(One):
            def __init__(self, two: int, three: int):
                super().__init__(one=2, two=two)
                self.three = three

        want = Dis(Two)

        assert want.fields == [
            strcs.Field(
                name="one",
                disassembled_type=Dis(int),
                owner=One,
                original_owner=One,
            ),
            strcs.Field(
                name="two",
                disassembled_type=Dis(int),
                owner=Two,
                original_owner=One,
            ),
            strcs.Field(
                name="three",
                disassembled_type=Dis(int),
                owner=Two,
                original_owner=Two,
            ),
        ]

        thing = Two(two=3, three=4)
        assert thing.one == 2
        assert thing.two == 3
        assert thing.three == 4

        thing2 = reg.create(Two, {"two": 3, "three": 4})
        assert thing2.one == 2
        assert thing2.two == 3
        assert thing2.three == 4

        thing3 = reg.create(Two, {"one": 20, "two": 3, "three": 4})
        assert thing3.one == 2
        assert thing3.two == 3
        assert thing3.three == 4
