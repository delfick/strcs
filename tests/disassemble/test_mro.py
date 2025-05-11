import re
from collections import OrderedDict
from typing import Annotated, Generic, Optional, TypeVar

import attrs
import pytest

import strcs
from strcs.disassemble import MRO

Disassembler = strcs.disassemble.Disassembler


class TestAssumptions:
    def test_it_cant_do_a_generic_to_things_that_arent_type_var(self):
        with pytest.raises(
            TypeError,
            match=r"Parameters to Generic\[...\] must all be type variables or parameter specification variables.",
        ):

            class One(Generic[str]):  # type: ignore[misc]
                pass

    def test_it_cant_have_Generic_and_unfilled_generic_parents(self):
        T = TypeVar("T")
        U = TypeVar("U")

        class One(Generic[T]):
            pass

        with pytest.raises(TypeError, match="Cannot create a consistent method resolution"):

            class Two(Generic[U], One):
                pass

    def test_it_cant_do_a_diamond_of_two_of_the_same_type_with_different_parameters(self):
        T = TypeVar("T")

        class One(Generic[T]):
            pass

        with pytest.raises(TypeError, match="duplicate base class One"):

            class Two(One[int], One[bool]):  # type: ignore
                pass


class TestMRO:
    @pytest.mark.parametrize(
        "start",
        (
            0,
            1,
            True,
            False,
            (),
            (1,),
            [],
            [1],
            {},
            {1: 1},
            pytest.param(lambda: None, id="callable"),
            None,
        ),
    )
    def test_it_works_for_something_that_isnt_a_class(
        self, start: object, type_cache: strcs.TypeCache
    ):
        mro = MRO.create(start, type_cache=type_cache)
        assert mro.start is start
        assert mro.args == ()
        assert mro.origin is None
        assert mro.mro == ()
        assert mro.bases == []
        assert mro.typevars == OrderedDict()
        assert mro.signature_for_display == ""

    def test_it_works_for_object(self, type_cache: strcs.TypeCache):
        mro = MRO.create(object, type_cache=type_cache)
        assert mro.start is object
        assert mro.args == ()
        assert mro.origin == object
        assert mro.mro == (object,)
        assert mro.bases == []
        assert mro.typevars == OrderedDict()
        assert mro.signature_for_display == ""

    @pytest.mark.parametrize("start", (str, int))
    def test_it_works_for_a_builtin_class(self, start: type, type_cache: strcs.TypeCache):
        mro = MRO.create(start, type_cache=type_cache)
        assert mro.start is start
        assert mro.args == ()
        assert mro.origin == start
        assert mro.mro == (start, object)
        assert mro.bases == [object]
        assert mro.typevars == OrderedDict()
        assert mro.signature_for_display == ""

    def test_it_works_for_indexed_builtins(self, type_cache: strcs.TypeCache):
        start = dict[str, int]
        mro = MRO.create(start, type_cache=type_cache)
        assert mro.start is start
        assert mro.args == (str, int)
        assert mro.origin == dict
        assert mro.mro == (dict, object)
        assert mro.bases == [object]
        assert mro.typevars == OrderedDict([((dict, 1), str), ((dict, 2), int)])
        assert mro.signature_for_display == "str, int"

    def test_it_works_for_subclasses_of_indexed_builtins(self, type_cache: strcs.TypeCache):
        class One(dict[str, int]):
            pass

        mro = MRO.create(One, type_cache=type_cache)
        assert mro.start is One
        assert mro.args == ()
        assert mro.origin == One
        assert mro.mro == (One, dict, object)
        assert mro.bases == [dict[str, int]]
        assert mro.typevars == OrderedDict([((dict, 1), str), ((dict, 2), int)])
        assert mro.signature_for_display == ""

    def test_it_works_for_subclasses_of_nested_indexed_builtins(self, type_cache: strcs.TypeCache):
        class One(dict[str, dict[bool, int]]):
            pass

        mro = MRO.create(One, type_cache=type_cache)
        assert mro.start is One
        assert mro.args == ()
        assert mro.origin == One
        assert mro.mro == (One, dict, object)
        assert mro.bases == [dict[str, dict[bool, int]]]
        assert mro.typevars == OrderedDict([((dict, 1), str), ((dict, 2), dict[bool, int])])
        assert mro.signature_for_display == ""

    def test_it_does_not_duplicate_when_the_same_class_appears_multiple_times_with_different_typevars(
        self, type_cache: strcs.TypeCache
    ):
        class One(dict[str, int]):
            pass

        class Two(One, dict[bool, str]):
            pass

        mro = MRO.create(Two, type_cache=type_cache)
        assert mro.start is Two
        assert mro.args == ()
        assert mro.origin == Two
        assert mro.mro == (Two, One, dict, object)
        assert mro.bases == [One, dict[bool, str]]
        assert mro.typevars == OrderedDict([((dict, 1), str), ((dict, 2), int)])

    def test_it_works_for_a_simple_class(self, type_cache: strcs.TypeCache):
        class One:
            pass

        mro = MRO.create(One, type_cache=type_cache)
        assert mro.start is One
        assert mro.args == ()
        assert mro.origin == One
        assert mro.mro == (One, object)
        assert mro.bases == [object]
        assert mro.typevars == OrderedDict()
        assert mro.signature_for_display == ""

    def test_it_works_for_a_simple_hierarchy(self, type_cache: strcs.TypeCache):
        class One:
            pass

        class Two(One):
            pass

        class Three(Two):
            pass

        mro = MRO.create(Three, type_cache=type_cache)
        assert mro.start is Three
        assert mro.args == ()
        assert mro.origin == Three
        assert mro.mro == (Three, Two, One, object)
        assert mro.bases == [Two, One, object]
        assert mro.typevars == OrderedDict()
        assert mro.signature_for_display == ""

    def test_it_works_for_multiple_inheritance(self, type_cache: strcs.TypeCache):
        class A:
            pass

        class B:
            pass

        class C(A, B):
            pass

        class D:
            pass

        class E:
            pass

        class F(D, E):
            pass

        class G(C, F):
            pass

        mro = MRO.create(G, type_cache=type_cache)
        assert mro.start is G
        assert mro.args == ()
        assert mro.origin == G
        assert mro.mro == (G, C, A, B, F, D, E, object)
        assert mro.bases == [C, A, B, F, D, E, object]
        assert mro.typevars == OrderedDict()
        assert mro.signature_for_display == ""

    def test_it_works_for_simple_generic(self, type_cache: strcs.TypeCache):
        T = TypeVar("T")

        class One(Generic[T]):
            pass

        mro = MRO.create(One, type_cache=type_cache)
        assert mro.start is One
        assert mro.args == ()
        assert mro.origin == One
        assert mro.mro == (One, Generic, object)
        assert mro.bases == [Generic[T]]
        assert mro.typevars == OrderedDict([((One, T), strcs.Type.Missing)])
        assert mro.signature_for_display == "~T"

        mro = MRO.create(One[int], type_cache=type_cache)
        assert mro.start is One[int]
        assert mro.args == (int,)
        assert mro.origin == One
        assert mro.mro == (One, Generic, object)
        assert mro.bases == [Generic[T]]
        assert mro.typevars == OrderedDict([((One, T), int)])
        assert mro.signature_for_display == "int"

    def test_it_knows_unfilled_typevars_of_the_parent(self, type_cache: strcs.TypeCache):
        T = TypeVar("T")

        class One(Generic[T]):
            pass

        class Two(One):
            pass

        class Three(Two):
            pass

        mro = MRO.create(Three, type_cache=type_cache)
        assert mro.start is Three
        assert mro.args == ()
        assert mro.origin == Three
        assert mro.mro == (Three, Two, One, Generic, object)
        assert mro.bases == [Two, One, Generic, object]
        assert mro.typevars == OrderedDict([((One, T), strcs.Type.Missing)])
        assert mro.signature_for_display == "~T"

    def test_it_knows_multiple_unfilled_typevars_of_the_parent(self, type_cache: strcs.TypeCache):
        T = TypeVar("T")
        U = TypeVar("U")

        class One(Generic[T]):
            pass

        class Two(One, Generic[U]):
            pass

        class Three(Two):
            pass

        mro = MRO.create(Three, type_cache=type_cache)
        assert mro.start is Three
        assert mro.args == ()
        assert mro.origin == Three
        assert mro.mro == (Three, Two, One, Generic, object)
        assert mro.bases == [Two, One, Generic, object]
        assert mro.typevars == OrderedDict(
            [((Two, U), strcs.Type.Missing), ((One, T), strcs.Type.Missing)]
        )
        # Can't access T from the signature
        assert mro.signature_for_display == "~U"

        class Four(Two[int]):
            pass

        mro = MRO.create(Four, type_cache=type_cache)
        assert mro.start is Four
        assert mro.args == ()
        assert mro.origin == Four
        assert mro.mro == (Four, Two, One, Generic, object)
        assert mro.bases == [Two[int]]
        assert mro.typevars == OrderedDict([((Two, U), int), ((One, T), strcs.Type.Missing)])
        # Can't access T from the signature
        assert mro.signature_for_display == ""

    def test_it_cant_partially_fill_out_type_vars(self, type_cache: strcs.TypeCache):
        # Sanity check for python error in version of python at time of writing
        T = TypeVar("T")
        U = TypeVar("U")

        class One(Generic[T, U]):
            pass

        with pytest.raises(TypeError, match="Too few (arguments|parameters)"):

            class Two(One[int]):  # type: ignore[type-arg]
                pass

    def test_it_works_for_multiple_generic_hierarchy(self, type_cache: strcs.TypeCache):
        T = TypeVar("T")
        U = TypeVar("U")

        assert isinstance(T, TypeVar)
        assert isinstance(U, TypeVar)

        class One(Generic[T]):
            pass

        class Two(Generic[U]):
            pass

        class Three(Generic[U, T], Two[U], One[T]):
            pass

        mro = MRO.create(Three, type_cache=type_cache)
        assert mro.start is Three
        assert mro.args == ()
        assert mro.origin == Three
        assert mro.mro == (Three, Two, One, Generic, object)
        assert mro.bases == [Generic[U, T], Two[U], One[T]]  # type: ignore[valid-type]
        assert mro.typevars == OrderedDict(
            [
                ((Three, U), strcs.Type.Missing),
                ((Three, T), strcs.Type.Missing),
                ((Two, U), MRO.Referal(owner=Three, typevar=U, value=strcs.Type.Missing)),
                ((One, T), MRO.Referal(owner=Three, typevar=T, value=strcs.Type.Missing)),
            ]
        )
        assert mro.signature_for_display == "~U, ~T"

        start = Three[str, int]
        mro = MRO.create(start, type_cache=type_cache)
        assert mro.start is start
        assert mro.args == (str, int)
        assert mro.origin == Three
        assert mro.mro == (Three, Two, One, Generic, object)
        assert mro.bases == [Generic[U, T], Two[U], One[T]]  # type: ignore[valid-type]
        assert mro.typevars == OrderedDict(
            [
                ((Three, U), str),
                ((Three, T), int),
                ((Two, U), MRO.Referal(owner=Three, typevar=U, value=str)),
                ((One, T), MRO.Referal(owner=Three, typevar=T, value=int)),
            ]
        )
        assert mro.signature_for_display == "str, int"

    def test_it_works_for_partially_filled_generic_hierarchy(self, type_cache: strcs.TypeCache):
        T = TypeVar("T")
        U = TypeVar("U")
        Z = TypeVar("Z")

        assert isinstance(Z, TypeVar)

        class One(Generic[T]):
            pass

        class Two(Generic[U]):
            pass

        class Three(Generic[Z], Two[Z], One[str]):
            pass

        mro = MRO.create(Three, type_cache=type_cache)
        assert mro.start is Three
        assert mro.args == ()
        assert mro.origin == Three
        assert mro.mro == (Three, Two, One, Generic, object)
        assert mro.bases == [Generic[Z], Two[Z], One[str]]  # type: ignore[valid-type]
        assert mro.typevars == OrderedDict(
            [
                ((Three, Z), strcs.Type.Missing),
                ((Two, U), MRO.Referal(owner=Three, typevar=Z, value=strcs.Type.Missing)),
                ((One, T), str),
            ]
        )
        assert mro.signature_for_display == "~Z"

        start = Three[bool]
        mro = MRO.create(start, type_cache=type_cache)
        assert mro.start is start
        assert mro.args == (bool,)
        assert mro.origin == Three
        assert mro.mro == (Three, Two, One, Generic, object)
        assert mro.bases == [Generic[Z], Two[Z], One[str]]  # type: ignore[valid-type]
        assert mro.typevars == OrderedDict(
            [
                ((Three, Z), bool),
                ((Two, U), MRO.Referal(owner=Three, typevar=Z, value=bool)),
                ((One, T), str),
            ]
        )
        assert mro.signature_for_display == "bool"

    def test_it_works_for_fully_filled_generic_hierarchy(self, type_cache: strcs.TypeCache):
        T = TypeVar("T")
        U = TypeVar("U")
        Z = TypeVar("Z")

        assert isinstance(Z, TypeVar)

        class One(Generic[T]):
            pass

        class Two(Generic[U]):
            pass

        class Three(Generic[Z], Two[Z], One[str]):
            pass

        class Four(Three[int]):
            pass

        mro = MRO.create(Four, type_cache=type_cache)
        assert mro.start is Four
        assert mro.args == ()
        assert mro.origin == Four
        assert mro.mro == (Four, Three, Two, One, Generic, object)
        assert mro.bases == [Three[int]]
        assert mro.typevars == OrderedDict(
            [
                ((Three, Z), int),
                ((Two, U), MRO.Referal(owner=Three, typevar=Z, value=int)),
                ((One, T), str),
            ]
        )
        assert mro.signature_for_display == ""

    def test_it_works_for_generics_filled_with_other_generics(self, type_cache: strcs.TypeCache):
        T = TypeVar("T")
        U = TypeVar("U")

        class One(Generic[T]):
            pass

        class Two(Generic[U]):
            pass

        class Three(Two[One[str]]):
            pass

        mro = MRO.create(Three, type_cache=type_cache)
        assert mro.start is Three
        assert mro.args == ()
        assert mro.origin == Three
        assert mro.mro == (Three, Two, Generic, object)
        assert mro.bases == [Two[One[str]]]
        assert mro.typevars == OrderedDict([((Two, U), One[str])])
        assert mro.signature_for_display == ""

    def test_it_works_for_generics_filled_multiple_times(self, type_cache: strcs.TypeCache):
        T = TypeVar("T")
        U = TypeVar("U")
        Z = TypeVar("Z")

        assert isinstance(Z, TypeVar)
        assert isinstance(U, TypeVar)

        class One(Generic[T]):
            pass

        class Two(Generic[U], One[U]):
            pass

        class Three(Generic[Z], Two[Z]):
            pass

        mro = MRO.create(Three, type_cache=type_cache)
        assert mro.start is Three
        assert mro.args == ()
        assert mro.origin == Three
        assert mro.mro == (Three, Two, One, Generic, object)
        assert mro.bases == [Generic[Z], Two[Z]]  # type: ignore[valid-type]
        assert mro.typevars == OrderedDict(
            [
                ((Three, Z), strcs.Type.Missing),
                ((Two, U), MRO.Referal(owner=Three, typevar=Z, value=strcs.Type.Missing)),
                ((One, T), MRO.Referal(owner=Two, typevar=U, value=strcs.Type.Missing)),
            ]
        )

        assert MRO.create(Three[str], type_cache=type_cache).typevars == OrderedDict(
            [
                ((Three, Z), str),
                ((Two, U), MRO.Referal(owner=Three, typevar=Z, value=str)),
                ((One, T), MRO.Referal(owner=Two, typevar=U, value=str)),
            ]
        )
        assert MRO.create(Three[str | int], type_cache=type_cache).typevars == OrderedDict(
            [
                ((Three, Z), str | int),
                ((Two, U), MRO.Referal(owner=Three, typevar=Z, value=str | int)),
                ((One, T), MRO.Referal(owner=Two, typevar=U, value=str | int)),
            ]
        )
        assert mro.signature_for_display == "~Z"

    def test_it_can_get_vars_from_container(self, type_cache: strcs.TypeCache):
        start = dict[int, str]

        mro = MRO.create(start, type_cache=type_cache)
        assert mro.start is start
        assert mro.args == (int, str)
        assert mro.origin == dict
        assert mro.mro == (dict, object)
        assert mro.bases == [object]
        assert mro.typevars == OrderedDict(
            [
                ((dict, 1), int),
                ((dict, 2), str),
            ]
        )
        assert mro.all_vars == (int, str)
        assert mro.signature_for_display == "int, str"

    def test_it_can_get_vars_when_inheriting_from_container(self, type_cache: strcs.TypeCache):
        class One(dict[int, str]):
            pass

        mro = MRO.create(One, type_cache=type_cache)
        assert mro.start is One
        assert mro.args == ()
        assert mro.origin == One
        assert mro.mro == (One, dict, object)
        assert mro.bases == [dict[int, str]]
        assert mro.typevars == OrderedDict(
            [
                ((dict, 1), int),
                ((dict, 2), str),
            ]
        )
        assert mro.all_vars == (int, str)
        assert mro.signature_for_display == ""

    def test_it_can_get_fields(self, type_cache: strcs.TypeCache, Dis: Disassembler):
        T = TypeVar("T")
        U = TypeVar("U")

        class One(Generic[T, U]):
            def __init__(self, one: T, two: U):
                self.one = one
                self.two = two

        class Two(One[str, int]):
            pass

        mro = MRO.create(Two, type_cache=type_cache)

        assert mro.raw_fields == [
            strcs.Field(name="one", owner=Two, original_owner=One, disassembled_type=Dis(T)),
            strcs.Field(name="two", owner=Two, original_owner=One, disassembled_type=Dis(U)),
        ]

        assert mro.fields == [
            strcs.Field(name="one", owner=Two, original_owner=One, disassembled_type=Dis(str)),
            strcs.Field(name="two", owner=Two, original_owner=One, disassembled_type=Dis(int)),
        ]

    def test_it_can_get_fields_with_modified_types(
        self, type_cache: strcs.TypeCache, Dis: Disassembler
    ):
        T = TypeVar("T")
        U = TypeVar("U")

        @attrs.define
        class One(Generic[T, U]):
            one: T | None
            two: Annotated[U, "hello"]

        @attrs.define
        class Two(One[str, int]):
            pass

        mro = MRO.create(Two, type_cache=type_cache)

        assert mro.raw_fields == [
            strcs.Field(
                name="one", owner=Two, original_owner=One, disassembled_type=Dis(Optional[T])
            ),
            strcs.Field(
                name="two",
                owner=Two,
                original_owner=One,
                disassembled_type=Dis(Annotated[U, "hello"]),
            ),
        ]

        assert mro.fields == [
            strcs.Field(
                name="one", owner=Two, original_owner=One, disassembled_type=Dis(Optional[str])
            ),
            strcs.Field(
                name="two",
                owner=Two,
                original_owner=One,
                disassembled_type=Dis(Annotated[int, "hello"]),
            ),
        ]

        @attrs.define
        class Three(Generic[T, U], One[T, U]):
            one: T

        @attrs.define
        class Four(Three[str, int]):
            pass

        mro = MRO.create(Four, type_cache=type_cache)

        assert mro.raw_fields == [
            strcs.Field(name="one", owner=Four, original_owner=Three, disassembled_type=Dis(T)),
            strcs.Field(
                name="two",
                owner=Four,
                original_owner=One,
                disassembled_type=Dis(Annotated[U, "hello"]),
            ),
        ]

        assert mro.fields == [
            strcs.Field(name="one", owner=Four, original_owner=Three, disassembled_type=Dis(str)),
            strcs.Field(
                name="two",
                owner=Four,
                original_owner=One,
                disassembled_type=Dis(Annotated[int, "hello"]),
            ),
        ]

    class TestFindingProvidedSubtype:
        def test_it_can_find_the_provided_subtype(self, type_cache: strcs.TypeCache):
            class Item:
                pass

            class ItemA(Item):
                pass

            class ItemB(Item):
                pass

            class ItemC(Item):
                pass

            I = TypeVar("I", bound=Item)

            class Container(Generic[I]):
                pass

            container_a = strcs.MRO.create(Container[ItemA], type_cache=type_cache)
            container_b = strcs.MRO.create(Container[ItemB], type_cache=type_cache)
            container_c = strcs.MRO.create(Container[ItemC], type_cache=type_cache)

            assert container_a.find_subtypes(Item) == (ItemA,)
            assert container_b.find_subtypes(Item) == (ItemB,)
            assert container_c.find_subtypes(Item) == (ItemC,)

        def test_it_can_find_multiple_subtypes(self, type_cache: strcs.TypeCache):
            class One:
                pass

            class Two:
                pass

            class OneA(One):
                pass

            class OneB(One):
                pass

            class TwoA(Two):
                pass

            class TwoB(Two):
                pass

            O = TypeVar("O", bound=One)
            T = TypeVar("T", bound=Two)

            class Container(Generic[O, T]):
                pass

            container_a = strcs.MRO.create(Container[OneA, TwoB], type_cache=type_cache)
            container_b = strcs.MRO.create(Container[OneB, TwoB], type_cache=type_cache)

            assert container_a.find_subtypes(One, Two) == (OneA, TwoB)
            assert container_b.find_subtypes(One, Two) == (OneB, TwoB)

        def test_it_can_find_a_partial_number_of_subtypes(self, type_cache: strcs.TypeCache):
            class One:
                pass

            class Two:
                pass

            class OneA(One):
                pass

            class OneB(One):
                pass

            class TwoA(Two):
                pass

            class TwoB(Two):
                pass

            O = TypeVar("O", bound=One)
            T = TypeVar("T", bound=Two)

            class Container(Generic[O, T]):
                pass

            container_a = strcs.MRO.create(Container[OneA, TwoA], type_cache=type_cache)
            assert container_a.find_subtypes(One) == (OneA,)

        def test_it_complains_if_want_too_many_types(self, type_cache: strcs.TypeCache):
            class One:
                pass

            class Two:
                pass

            class OneA(One):
                pass

            class OneB(One):
                pass

            O = TypeVar("O", bound=One)

            class Container(Generic[O]):
                pass

            container_a = strcs.MRO.create(Container[OneA], type_cache=type_cache)
            with pytest.raises(
                ValueError, match=re.escape("The type has less typevars (1) than wanted (2)")
            ):
                container_a.find_subtypes(One, Two)

        def test_it_complains_if_want_wrong_subtype(self, type_cache: strcs.TypeCache):
            class One:
                pass

            class Two:
                pass

            class OneA(One):
                pass

            class OneB(One):
                pass

            O = TypeVar("O", bound=One)

            class Container(Generic[O]):
                pass

            container_a = strcs.MRO.create(Container[OneA], type_cache=type_cache)
            with pytest.raises(
                ValueError,
                match="The concrete type <class '[^']+'> is not a subclass of what was asked for <class '[^']+'>",
            ):
                container_a.find_subtypes(Two)
