# coding: spec
import re
import typing as tp
from collections import OrderedDict

import attrs
import pytest

import strcs
from strcs.type_tree import MRO


@pytest.fixture()
def type_cache() -> strcs.TypeCache:
    return strcs.TypeCache()


describe "assumptions":
    it "can't do a generic to things that aren't type var":
        with pytest.raises(
            TypeError,
            match=r"Parameters to Generic\[...\] must all be type variables or parameter specification variables.",
        ):

            class One(tp.Generic[str]):  # type: ignore[misc]
                pass

    it "can't have Generic and unfilled generic parents":
        T = tp.TypeVar("T")
        U = tp.TypeVar("U")

        class One(tp.Generic[T]):
            pass

        with pytest.raises(TypeError, match="Cannot create a consistent method resolution"):

            class Two(tp.Generic[U], One):
                pass

    it "can't do a diamond of two of the same type with different parameters":
        T = tp.TypeVar("T")

        class One(tp.Generic[T]):
            pass

        with pytest.raises(TypeError, match="duplicate base class One"):

            class Two(One[int], One[bool]):  # type: ignore
                pass

describe "MRO":

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
    it "works for something that isn't a class", start: object, type_cache: strcs.TypeCache:
        mro = MRO.create(start, type_cache=type_cache)
        assert mro.start is start
        assert mro.args == ()
        assert mro.origin is None
        assert mro.mro == ()
        assert mro.bases == []
        assert mro.typevars == OrderedDict()
        assert mro.signature_for_display == ""

    it "works for object", type_cache: strcs.TypeCache:
        mro = MRO.create(object, type_cache=type_cache)
        assert mro.start is object
        assert mro.args == ()
        assert mro.origin == object
        assert mro.mro == (object,)
        assert mro.bases == []
        assert mro.typevars == OrderedDict()
        assert mro.signature_for_display == ""

    @pytest.mark.parametrize("start", (str, int))
    it "works for a builtin class", start: type, type_cache: strcs.TypeCache:
        mro = MRO.create(start, type_cache=type_cache)
        assert mro.start is start
        assert mro.args == ()
        assert mro.origin == start
        assert mro.mro == (start, object)
        assert mro.bases == [object]
        assert mro.typevars == OrderedDict()
        assert mro.signature_for_display == ""

    it "works for indexed builtins", type_cache: strcs.TypeCache:
        start = dict[str, int]
        mro = MRO.create(start, type_cache=type_cache)
        assert mro.start is start
        assert mro.args == (str, int)
        assert mro.origin == dict
        assert mro.mro == (dict, object)
        assert mro.bases == [object]
        assert mro.typevars == OrderedDict([((dict, 1), str), ((dict, 2), int)])
        assert mro.signature_for_display == "str, int"

    it "works for subclasses of indexed builtins", type_cache: strcs.TypeCache:

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

    it "works for subclasses of nested indexed builtins", type_cache: strcs.TypeCache:

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

    it "does not duplicate when the same class appears multiple times with different typevars", type_cache: strcs.TypeCache:

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

    it "works for a simple class", type_cache: strcs.TypeCache:

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

    it "works for a simple hierarchy", type_cache: strcs.TypeCache:

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

    it "works for multiple inheritance", type_cache: strcs.TypeCache:

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

    it "works for simple generic", type_cache: strcs.TypeCache:
        T = tp.TypeVar("T")

        class One(tp.Generic[T]):
            pass

        mro = MRO.create(One, type_cache=type_cache)
        assert mro.start is One
        assert mro.args == ()
        assert mro.origin == One
        assert mro.mro == (One, tp.Generic, object)
        assert mro.bases == [tp.Generic[T]]
        assert mro.typevars == OrderedDict([((One, T), strcs.Type.Missing)])
        assert mro.signature_for_display == "~T"

        mro = MRO.create(One[int], type_cache=type_cache)
        assert mro.start is One[int]
        assert mro.args == (int,)
        assert mro.origin == One
        assert mro.mro == (One, tp.Generic, object)
        assert mro.bases == [tp.Generic[T]]
        assert mro.typevars == OrderedDict([((One, T), int)])
        assert mro.signature_for_display == "int"

    it "knows unfilled typevars of the parent", type_cache: strcs.TypeCache:
        T = tp.TypeVar("T")

        class One(tp.Generic[T]):
            pass

        class Two(One):
            pass

        class Three(Two):
            pass

        mro = MRO.create(Three, type_cache=type_cache)
        assert mro.start is Three
        assert mro.args == ()
        assert mro.origin == Three
        assert mro.mro == (Three, Two, One, tp.Generic, object)
        assert mro.bases == [Two, One, tp.Generic, object]
        assert mro.typevars == OrderedDict([((One, T), strcs.Type.Missing)])
        assert mro.signature_for_display == "~T"

    it "knows multiple unfilled typevars of the parent", type_cache: strcs.TypeCache:
        T = tp.TypeVar("T")
        U = tp.TypeVar("U")

        class One(tp.Generic[T]):
            pass

        class Two(One, tp.Generic[U]):
            pass

        class Three(Two):
            pass

        mro = MRO.create(Three, type_cache=type_cache)
        assert mro.start is Three
        assert mro.args == ()
        assert mro.origin == Three
        assert mro.mro == (Three, Two, One, tp.Generic, object)
        assert mro.bases == [Two, One, tp.Generic, object]
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
        assert mro.mro == (Four, Two, One, tp.Generic, object)
        assert mro.bases == [Two[int]]
        assert mro.typevars == OrderedDict([((Two, U), int), ((One, T), strcs.Type.Missing)])
        # Can't access T from the signature
        assert mro.signature_for_display == ""

    it "can't partially fill out type vars", type_cache: strcs.TypeCache:
        # Sanity check for python error in version of python at time of writing
        T = tp.TypeVar("T")
        U = tp.TypeVar("U")

        class One(tp.Generic[T, U]):
            pass

        with pytest.raises(TypeError, match="Too few arguments"):

            class Two(One[int]):  # type: ignore[type-arg]
                pass

    it "works for multiple generic hierarchy", type_cache: strcs.TypeCache:
        T = tp.TypeVar("T")
        U = tp.TypeVar("U")

        assert isinstance(T, tp.TypeVar)
        assert isinstance(U, tp.TypeVar)

        class One(tp.Generic[T]):
            pass

        class Two(tp.Generic[U]):
            pass

        class Three(tp.Generic[U, T], Two[U], One[T]):
            pass

        mro = MRO.create(Three, type_cache=type_cache)
        assert mro.start is Three
        assert mro.args == ()
        assert mro.origin == Three
        assert mro.mro == (Three, Two, One, tp.Generic, object)
        assert mro.bases == [tp.Generic[U, T], Two[U], One[T]]  # type: ignore[valid-type]
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
        assert mro.mro == (Three, Two, One, tp.Generic, object)
        assert mro.bases == [tp.Generic[U, T], Two[U], One[T]]  # type: ignore[valid-type]
        assert mro.typevars == OrderedDict(
            [
                ((Three, U), str),
                ((Three, T), int),
                ((Two, U), MRO.Referal(owner=Three, typevar=U, value=str)),
                ((One, T), MRO.Referal(owner=Three, typevar=T, value=int)),
            ]
        )
        assert mro.signature_for_display == "str, int"

    it "works for partially filled generic hierarchy", type_cache: strcs.TypeCache:
        T = tp.TypeVar("T")
        U = tp.TypeVar("U")
        Z = tp.TypeVar("Z")

        assert isinstance(Z, tp.TypeVar)

        class One(tp.Generic[T]):
            pass

        class Two(tp.Generic[U]):
            pass

        class Three(tp.Generic[Z], Two[Z], One[str]):
            pass

        mro = MRO.create(Three, type_cache=type_cache)
        assert mro.start is Three
        assert mro.args == ()
        assert mro.origin == Three
        assert mro.mro == (Three, Two, One, tp.Generic, object)
        assert mro.bases == [tp.Generic[Z], Two[Z], One[str]]  # type: ignore[valid-type]
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
        assert mro.mro == (Three, Two, One, tp.Generic, object)
        assert mro.bases == [tp.Generic[Z], Two[Z], One[str]]  # type: ignore[valid-type]
        assert mro.typevars == OrderedDict(
            [
                ((Three, Z), bool),
                ((Two, U), MRO.Referal(owner=Three, typevar=Z, value=bool)),
                ((One, T), str),
            ]
        )
        assert mro.signature_for_display == "bool"

    it "works for fully filled generic hierarchy", type_cache: strcs.TypeCache:
        T = tp.TypeVar("T")
        U = tp.TypeVar("U")
        Z = tp.TypeVar("Z")

        assert isinstance(Z, tp.TypeVar)

        class One(tp.Generic[T]):
            pass

        class Two(tp.Generic[U]):
            pass

        class Three(tp.Generic[Z], Two[Z], One[str]):
            pass

        class Four(Three[int]):
            pass

        mro = MRO.create(Four, type_cache=type_cache)
        assert mro.start is Four
        assert mro.args == ()
        assert mro.origin == Four
        assert mro.mro == (Four, Three, Two, One, tp.Generic, object)
        assert mro.bases == [Three[int]]
        assert mro.typevars == OrderedDict(
            [
                ((Three, Z), int),
                ((Two, U), MRO.Referal(owner=Three, typevar=Z, value=int)),
                ((One, T), str),
            ]
        )
        assert mro.signature_for_display == ""

    it "works for generics filled with other generics", type_cache: strcs.TypeCache:
        T = tp.TypeVar("T")
        U = tp.TypeVar("U")

        class One(tp.Generic[T]):
            pass

        class Two(tp.Generic[U]):
            pass

        class Three(Two[One[str]]):
            pass

        mro = MRO.create(Three, type_cache=type_cache)
        assert mro.start is Three
        assert mro.args == ()
        assert mro.origin == Three
        assert mro.mro == (Three, Two, tp.Generic, object)
        assert mro.bases == [Two[One[str]]]
        assert mro.typevars == OrderedDict([((Two, U), One[str])])
        assert mro.signature_for_display == ""

    it "works for generics filled multiple times", type_cache: strcs.TypeCache:
        T = tp.TypeVar("T")
        U = tp.TypeVar("U")
        Z = tp.TypeVar("Z")

        assert isinstance(Z, tp.TypeVar)
        assert isinstance(U, tp.TypeVar)

        class One(tp.Generic[T]):
            pass

        class Two(tp.Generic[U], One[U]):
            pass

        class Three(tp.Generic[Z], Two[Z]):
            pass

        mro = MRO.create(Three, type_cache=type_cache)
        assert mro.start is Three
        assert mro.args == ()
        assert mro.origin == Three
        assert mro.mro == (Three, Two, One, tp.Generic, object)
        assert mro.bases == [tp.Generic[Z], Two[Z]]  # type: ignore[valid-type]
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

    it "can get vars from container", type_cache: strcs.TypeCache:

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

    it "can get vars when inheriting from container", type_cache: strcs.TypeCache:

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

    it "can get fields", type_cache: strcs.TypeCache:

        T = tp.TypeVar("T")
        U = tp.TypeVar("U")

        class One(tp.Generic[T, U]):
            def __init__(self, one: T, two: U):
                self.one = one
                self.two = two

        class Two(One[str, int]):
            pass

        mro = MRO.create(Two, type_cache=type_cache)

        assert mro.raw_fields == [
            strcs.Field(name="one", owner=Two, original_owner=One, type=T),
            strcs.Field(name="two", owner=Two, original_owner=One, type=U),
        ]

        assert mro.fields == [
            strcs.Field(name="one", owner=Two, original_owner=One, type=str),
            strcs.Field(name="two", owner=Two, original_owner=One, type=int),
        ]

    it "can get fields with modified types", type_cache: strcs.TypeCache:

        T = tp.TypeVar("T")
        U = tp.TypeVar("U")

        @attrs.define
        class One(tp.Generic[T, U]):
            one: T | None
            two: tp.Annotated[U, "hello"]

        @attrs.define
        class Two(One[str, int]):
            pass

        mro = MRO.create(Two, type_cache=type_cache)

        assert mro.raw_fields == [
            strcs.Field(name="one", owner=Two, original_owner=One, type=tp.Optional[T]),
            strcs.Field(name="two", owner=Two, original_owner=One, type=tp.Annotated[U, "hello"]),
        ]

        assert mro.fields == [
            strcs.Field(name="one", owner=Two, original_owner=One, type=tp.Optional[str]),
            strcs.Field(name="two", owner=Two, original_owner=One, type=tp.Annotated[int, "hello"]),
        ]

        @attrs.define
        class Three(tp.Generic[T, U], One[T, U]):
            one: T

        @attrs.define
        class Four(Three[str, int]):
            pass

        mro = MRO.create(Four, type_cache=type_cache)

        assert mro.raw_fields == [
            strcs.Field(name="one", owner=Four, original_owner=Three, type=T),
            strcs.Field(name="two", owner=Four, original_owner=One, type=tp.Annotated[U, "hello"]),
        ]

        assert mro.fields == [
            strcs.Field(name="one", owner=Four, original_owner=Three, type=str),
            strcs.Field(
                name="two", owner=Four, original_owner=One, type=tp.Annotated[int, "hello"]
            ),
        ]

    describe "Finding provided subtype":

        it "can find the provided subtype", type_cache: strcs.TypeCache:

            class Item:
                pass

            class ItemA(Item):
                pass

            class ItemB(Item):
                pass

            class ItemC(Item):
                pass

            I = tp.TypeVar("I", bound=Item)

            class Container(tp.Generic[I]):
                pass

            container_a = strcs.MRO.create(Container[ItemA], type_cache=type_cache)
            container_b = strcs.MRO.create(Container[ItemB], type_cache=type_cache)
            container_c = strcs.MRO.create(Container[ItemC], type_cache=type_cache)

            assert container_a.find_subtypes(Item) == (ItemA,)
            assert container_b.find_subtypes(Item) == (ItemB,)
            assert container_c.find_subtypes(Item) == (ItemC,)

        it "can find multiple subtypes", type_cache: strcs.TypeCache:

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

            O = tp.TypeVar("O", bound=One)
            T = tp.TypeVar("T", bound=Two)

            class Container(tp.Generic[O, T]):
                pass

            container_a = strcs.MRO.create(Container[OneA, TwoB], type_cache=type_cache)
            container_b = strcs.MRO.create(Container[OneB, TwoB], type_cache=type_cache)

            assert container_a.find_subtypes(One, Two) == (OneA, TwoB)
            assert container_b.find_subtypes(One, Two) == (OneB, TwoB)

        it "can find a partial number of subtypes", type_cache: strcs.TypeCache:

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

            O = tp.TypeVar("O", bound=One)
            T = tp.TypeVar("T", bound=Two)

            class Container(tp.Generic[O, T]):
                pass

            container_a = strcs.MRO.create(Container[OneA, TwoA], type_cache=type_cache)
            assert container_a.find_subtypes(One) == (OneA,)

        it "complains if want too many types", type_cache: strcs.TypeCache:

            class One:
                pass

            class Two:
                pass

            class OneA(One):
                pass

            class OneB(One):
                pass

            O = tp.TypeVar("O", bound=One)

            class Container(tp.Generic[O]):
                pass

            container_a = strcs.MRO.create(Container[OneA], type_cache=type_cache)
            with pytest.raises(
                ValueError, match=re.escape("The type has less typevars (1) than wanted (2)")
            ):
                container_a.find_subtypes(One, Two)

        it "complains if want wrong subtype", type_cache: strcs.TypeCache:

            class One:
                pass

            class Two:
                pass

            class OneA(One):
                pass

            class OneB(One):
                pass

            O = tp.TypeVar("O", bound=One)

            class Container(tp.Generic[O]):
                pass

            container_a = strcs.MRO.create(Container[OneA], type_cache=type_cache)
            with pytest.raises(
                ValueError,
                match="The concrete type <class '[^']+'> is not a subclass of what was asked for <class '[^']+'>",
            ):
                container_a.find_subtypes(Two)
