# coding: spec
import abc
import typing as tp
from collections import OrderedDict
from collections.abc import Iterator

import attrs
import pytest

import strcs

Distilled = strcs.disassemble.Distilled
Disassembler = strcs.disassemble.Disassembler


@pytest.fixture()
def comparer(type_cache: strcs.TypeCache) -> strcs.disassemble.Comparer:
    return strcs.disassemble.Comparer(type_cache)


@attrs.define
class MatchCheck:
    orig: object
    matches: tuple[object, ...] = attrs.field(factory=lambda: ())
    not_match: tuple[object, ...] = attrs.field(factory=lambda: ())


class Expander(tp.Protocol):
    def __call__(
        self, checking: object, check_against: object
    ) -> Iterator[tuple[object, object, bool]]:
        ...


class MatchAsserter(tp.Protocol):
    def __call__(
        self,
        *checks: MatchCheck,
        subclasses: bool = False,
        allow_missing_typevars: bool = False,
    ) -> None:
        ...


class Comparator(abc.ABC):
    got: object

    @abc.abstractmethod
    def do_check(self, o: object) -> bool:
        ...

    def do_repr(self, got: object) -> str:
        return repr(got)

    def __eq__(self, o: object) -> bool:
        self.got = o
        return self.do_check(o)

    def __repr__(self) -> str:
        if not hasattr(self, "got"):
            return f"<{self.__class__.__name__}>"
        else:
            return self.do_repr(self.got)


class ComparatorWithTypeRepr(Comparator):
    def do_repr(self, got: object) -> str:
        lines = [""]
        if not isinstance(got, tuple):
            got = (got,)

        for index, part in enumerate(got):
            lines.append(f"{index}: ({type(part)}) -> {repr(part)}")

        return f"[{self.__class__.__name__}[" + " >> ".join(lines) + "]]"


describe "Comparer":
    describe "Distill":
        it "treats None like type(None)", Dis: Disassembler, comparer: strcs.disassemble.Comparer:
            for dis in (
                None,
                tp.Annotated[None, "asdf"],
                Dis(None).checkable,
                type(None),
                Dis(type(None)),
                Dis(tp.Annotated[type(None), "asdf"]),
                Dis(type(None)).checkable,
            ):
                assert comparer.distill(dis) == Distilled.valid(type(None))

        it "can get the type when already a type", comparer: strcs.disassemble.Comparer:

            class Thing:
                pass

            for typ in (int, str, bool, dict, list, set, Thing):
                assert comparer.distill(typ) == Distilled(original=typ, is_valid=True)

        it "can distil a tuple", comparer: strcs.disassemble.Comparer:
            assert comparer.distill(()) == Distilled.valid(())
            assert comparer.distill((1,)) == Distilled.invalid(1)
            assert comparer.distill((int,)) == Distilled.valid(int)
            assert comparer.distill((int, str)) == Distilled.valid((int, str))

        it "can turn an optional in to a tuple", comparer: strcs.disassemble.Comparer:
            assert comparer.distill(tp.Optional[int]) == Distilled.valid((int, type(None)))
            assert comparer.distill(tp.Optional[int | str]) == Distilled.valid(
                (str, int, type(None))
            )
            assert comparer.distill(
                tp.Annotated[tp.Optional[int | str], "asdf"]
            ) == Distilled.valid((str, int, type(None)))
            assert comparer.distill(
                tp.Annotated[tp.Optional[int | tp.Annotated[str, "asdf"]], "asdf"]
            ) == Distilled.valid((str, int, type(None)))
            assert comparer.distill(
                tp.Annotated[tp.Optional[int | tp.Annotated[str | None, "asdf"]], "asdf"]
            ) == Distilled.valid((str, int, type(None)))

        it "doesn't confuse int and boolean", Dis: Disassembler, comparer: strcs.disassemble.Comparer:

            def clear() -> None:
                comparer.type_cache.clear()

            for thing in (
                True,
                1,
                clear,
                1,
                True,
                clear,
                False,
                0,
                clear,
                0,
                False,
                clear,
                True,
                1,
            ):
                if thing is clear:
                    clear()
                    continue
                assert comparer.distill(thing).original is thing
                assert comparer.distill(Dis(thing)).original is thing
                assert comparer.distill(Dis(thing).checkable).original is thing
                chck = Dis(thing).checkable
                want = tp.Annotated[chck, "asdf"]  # type: ignore[valid-type]
                assert hasattr(want, "__args__")
                assert want.__args__[0] is chck
                assert comparer.distill(want).original is thing

        it "can resolve to the original type", Dis: Disassembler, comparer: strcs.disassemble.Comparer:

            class Thing:
                pass

            class Exact(ComparatorWithTypeRepr):
                def do_check(self, o: object) -> bool:
                    return o is Thing

            class Optional(ComparatorWithTypeRepr):
                def do_check(self, o: object) -> bool:
                    return (
                        isinstance(o, tuple)
                        and len(o) == 2
                        and o[0] is Thing
                        and o[1] is type(None)
                    )

            for thing, expect in (
                (Thing, Exact()),
                (Thing | None, Optional()),
            ):
                assert comparer.distill(thing).original == expect
                assert comparer.distill(Dis(thing)).original == expect
                assert comparer.distill(Dis(Dis(thing))).original == expect
                assert comparer.distill(Dis(Dis(thing)).checkable).original == expect
                assert comparer.distill(Dis(Dis(Dis(thing)).checkable)).original == expect
                assert (
                    comparer.distill(
                        tp.Annotated[Dis(Dis(Dis(thing)).checkable).checkable, "asdf"]
                    ).original
                    == expect
                )
                assert (
                    comparer.distill(
                        Dis(tp.Annotated[Dis(Dis(Dis(thing)).checkable).checkable, "asdf"])
                    ).original
                    == expect
                )
                assert (
                    comparer.distill(
                        Dis(
                            tp.Annotated[Dis(Dis(Dis(thing)).checkable).checkable, "asdf"]
                        ).checkable
                    ).original
                    == expect
                )
                assert (
                    comparer.distill(
                        Dis(
                            Dis(
                                tp.Annotated[Dis(Dis(Dis(thing)).checkable).checkable, "asdf"]
                            ).checkable
                        )
                    ).original
                    == expect
                )

        it "can resolve a generic to it's original type", Dis: Disassembler, comparer: strcs.disassemble.Comparer:
            T = tp.TypeVar("T")

            class Thing(tp.Generic[T]):
                pass

            class Exact(ComparatorWithTypeRepr):
                def do_check(self, o: object) -> bool:
                    return o is Thing

            class Optional(ComparatorWithTypeRepr):
                def do_check(self, o: object) -> bool:
                    return (
                        isinstance(o, tuple)
                        and len(o) == 2
                        and o[0] is Thing
                        and o[1] is type(None)
                    )

            for thing, expect in (
                (Thing[int], Exact()),
                (Thing[int] | None, Optional()),
            ):
                assert comparer.distill(thing).original == expect
                assert comparer.distill(Dis(thing)).original == expect
                assert comparer.distill(Dis(Dis(thing))).original == expect
                assert comparer.distill(Dis(Dis(thing)).checkable).original == expect
                assert comparer.distill(Dis(Dis(Dis(thing)).checkable)).original == expect
                assert (
                    comparer.distill(
                        tp.Annotated[Dis(Dis(Dis(thing)).checkable).checkable, "asdf"]
                    ).original
                    == expect
                )
                assert (
                    comparer.distill(
                        Dis(tp.Annotated[Dis(Dis(Dis(thing)).checkable).checkable, "asdf"])
                    ).original
                    == expect
                )
                assert (
                    comparer.distill(
                        Dis(
                            tp.Annotated[Dis(Dis(Dis(thing)).checkable).checkable, "asdf"]
                        ).checkable
                    ).original
                    == expect
                )
                assert (
                    comparer.distill(
                        Dis(
                            Dis(
                                tp.Annotated[Dis(Dis(Dis(thing)).checkable).checkable, "asdf"]
                            ).checkable
                        )
                    ).original
                    == expect
                )

        it "can get the type from a strcs.Type of a type", Dis: Disassembler, comparer: strcs.disassemble.Comparer:

            class Thing:
                pass

            for typ in (int, str, bool, dict, list, set, Thing):
                assert comparer.distill(Dis(typ)) == Distilled.valid(typ)
                assert comparer.distill(Dis(tp.Union[typ, None])) == Distilled.valid(
                    (typ, type(None))
                )
                assert comparer.distill(
                    Dis(tp.Annotated[tp.Union[typ, None], "asdf"])
                ) == Distilled.valid((typ, type(None)))
                assert comparer.distill(
                    tp.Union[Dis(tp.Annotated[tp.Union[typ, None], "asdf"]).checkable, None]
                ) == Distilled.valid((typ, type(None)))
                assert comparer.distill(
                    tp.Union[Dis(tp.Annotated[typ, "asdf"]).checkable, None]
                ) == Distilled.valid((typ, type(None)))

        it "can get the type from a strcs.InstanceCheck of a type", Dis: Disassembler, comparer: strcs.disassemble.Comparer:

            class Thing:
                pass

            for typ in (int, str, bool, dict, list, set, Thing):
                assert comparer.distill(Dis(typ).checkable) == Distilled.valid(typ)
                assert comparer.distill(Dis(tp.Union[typ, None]).checkable) == Distilled.valid(
                    (typ, type(None))
                )
                assert comparer.distill(
                    Dis(tp.Annotated[tp.Union[typ, None], "asdf"]).checkable
                ) == Distilled.valid((typ, type(None)))
                assert comparer.distill(
                    tp.Union[Dis(tp.Annotated[tp.Union[typ, None], "asdf"]).checkable, None]
                ) == Distilled.valid((typ, type(None)))
                assert comparer.distill(
                    Dis(tp.Union[tp.Annotated[typ, "asdf"], None]).checkable
                ) == Distilled.valid((typ, type(None)))

        it "can get the type from strcs.Type of strcs.Type of strcs.Type of type", Dis: Disassembler, comparer: strcs.disassemble.Comparer:

            class Thing:
                pass

            dis1 = Dis(Thing)
            dis2 = Dis(dis1)
            dis3 = Dis(tp.Union[dis2.checkable, None])
            dis4 = Dis(tp.Annotated[dis3.checkable, "asdf"])
            dis5 = Dis(dis4)

            for dis in (dis1, dis2, dis3, dis4, dis5):
                if dis in (dis1, dis2):
                    assert comparer.distill(dis) == Distilled.valid(Thing)
                else:
                    assert comparer.distill(dis) == Distilled.valid((Thing, type(None)))

            for dis in (dis1, dis2, dis3, dis4, dis5):
                comparer.type_cache.clear()
                if dis in (dis1, dis2):
                    assert comparer.distill(dis) == Distilled.valid(Thing)
                else:
                    assert comparer.distill(dis) == Distilled.valid((Thing, type(None)))

        it "says tuples of types are valid", Dis: Disassembler, comparer: strcs.disassemble.Comparer:
            typ = int | str | bool
            assert comparer.distill(typ) == Distilled.valid((bool, str, int))
            assert comparer.distill(tp.Union[typ, None]) == Distilled.valid(
                (bool, str, int, type(None))
            )
            assert comparer.distill(tp.Annotated[tp.Union[typ, None], "asdf"]) == Distilled.valid(
                (bool, str, int, type(None))
            )

            assert comparer.distill((str, dict, list)) == Distilled.valid((str, dict, list))

        it "returns class of generics", Dis: Disassembler, comparer: strcs.disassemble.Comparer:
            T = tp.TypeVar("T")

            class Thing(tp.Generic[T]):
                pass

            for option in (Thing, Thing[int]):
                for with_extra, expected, expected_generic in (
                    (tp.Union[option, None], (Thing, type(None)), tp.Optional[option]),
                    (tp.Annotated[option, "asdf"], Thing, option),
                    (
                        tp.Union[tp.Annotated[option, "asdf"], None],
                        (Thing, type(None)),
                        tp.Optional[option],
                    ),
                    (
                        tp.Union[tp.Annotated[tp.Union[option, None], "asdf"], None],
                        (Thing, type(None)),
                        tp.Optional[option],
                    ),
                ):
                    assert comparer.distill(with_extra) == Distilled.valid(
                        expected, as_generic=expected_generic
                    )
                    assert comparer.distill(Dis(with_extra)) == Distilled.valid(
                        expected, as_generic=expected_generic
                    )
                    assert comparer.distill(Dis(with_extra).checkable) == Distilled.valid(
                        expected, as_generic=expected_generic
                    )
                    assert comparer.distill(
                        tp.Union[Dis(with_extra).checkable, None]
                    ) == Distilled.valid((Thing, type(None)), as_generic=tp.Optional[option])

        it "returns tuple of generics", Dis: Disassembler, comparer: strcs.disassemble.Comparer:
            T = tp.TypeVar("T")

            class Thing(tp.Generic[T]):
                pass

            U = tp.TypeVar("U")

            class Stuff(tp.Generic[U]):
                pass

            for option in (Thing | Stuff, Stuff[int] | Thing[str]):
                for with_extra, expected, expected_generic in (
                    (tp.Union[option, None], (Thing, Stuff, type(None)), tp.Optional[option]),
                    (tp.Annotated[option, "asdf"], (Thing, Stuff), option),
                    (
                        tp.Union[tp.Annotated[option, "asdf"], None],
                        (Thing, Stuff, type(None)),
                        tp.Optional[option],
                    ),
                    (
                        tp.Union[tp.Annotated[tp.Union[option, None], "asdf"], None],
                        (Thing, Stuff, type(None)),
                        tp.Optional[option],
                    ),
                ):
                    assert comparer.distill(with_extra) == Distilled.valid(
                        expected, as_generic=expected_generic
                    )
                    assert comparer.distill(Dis(with_extra)) == Distilled.valid(
                        expected, as_generic=expected_generic
                    )
                    assert comparer.distill(Dis(with_extra).checkable) == Distilled.valid(
                        expected, as_generic=expected_generic
                    )
                    assert comparer.distill(
                        tp.Union[Dis(with_extra).checkable, None]
                    ) == Distilled.valid((Thing, Stuff, type(None)), as_generic=tp.Optional[option])

        it "returns tuple of complex generics", Dis: Disassembler, comparer: strcs.disassemble.Comparer:
            T = tp.TypeVar("T")

            class Thing(tp.Generic[T]):
                pass

            U = tp.TypeVar("U")

            class Stuff(tp.Generic[U]):
                pass

            typ1: strcs.Type[object] = Dis(tp.Annotated[Thing[int], "adf"])
            typ2: object = tp.Annotated[typ1.checkable, "asdf"]
            typ3: strcs.Type[object] = Dis(Dis(typ2).checkable)
            typ4: object = tp.Union[typ3.checkable, str]

            typ5: object = Stuff[dict]
            typ6: strcs.Type[object] = Dis(tp.Annotated[typ5, "asdf"])
            typ7: object = tp.Optional[typ6.checkable]
            typ8: object = Dis(typ7).checkable

            typ9: object = Thing[typ6.checkable]  # type:ignore[name-defined]

            assert comparer.distill(tp.Union[typ4, typ8, bool, typ9]) == Distilled(
                original=(Thing, Stuff, bool, str, type(None)),
                is_valid=True,
                as_generic=tp.Union[
                    str,
                    bool,
                    Stuff[dict],
                    Thing[int],
                    Thing[typ6.checkable],  # type: ignore[name-defined]
                    type(None),
                ],
            )

        it "says complex stuff is valid when it is", Dis: Disassembler, comparer: strcs.disassemble.Comparer:
            provided = tp.Union[
                tp.Annotated[list[int], "str"], tp.Annotated[int | str | None, '"hello']
            ]
            assert comparer.distill(provided) == Distilled.valid(
                (str, int, list, type(None)), as_generic=tp.Optional[str | int | list[int]]
            )

            assert comparer.distill(tp.Union[provided, dict]) == Distilled.valid(
                (str, int, list, dict, type(None)),
                as_generic=tp.Optional[str | int | list[int] | dict],
            )

            assert comparer.distill(Dis(tp.Union[provided, dict])) == Distilled.valid(
                (str, int, list, dict, type(None)),
                as_generic=tp.Optional[str | int | list[int] | dict],
            )

            assert comparer.distill(
                tp.Union[Dis(tp.Union[provided, dict]).checkable, None]
            ) == Distilled.valid(
                (str, int, list, dict, type(None)),
                as_generic=tp.Optional[str | int | list[int] | dict],
            )

            assert comparer.distill(tp.Union[list[int], list[str]]) == Distilled.valid(
                list, as_generic=list[int] | list[str]
            )

        it "says tuples of not types are invalid", Dis: Disassembler, comparer: strcs.disassemble.Comparer:
            assert comparer.distill((1, [], list)) == Distilled.invalid((1, [], list))

        it "says not types are invalid", Dis: Disassembler, comparer: strcs.disassemble.Comparer:
            assert comparer.distill(1) == Distilled.invalid(1)
            assert comparer.distill([]) == Distilled.invalid([])

        it "can follow chains to not types", Dis: Disassembler, comparer: strcs.disassemble.Comparer:
            dis1 = Dis({})
            dis2 = Dis(dis1)
            dis3 = Dis(tp.Annotated[dis2.checkable, "asdf"])
            dis4 = Dis(dis3)

            for dis in (dis1, dis2, dis3, dis4):
                assert comparer.distill(dis) == Distilled.invalid({})

            for dis in (dis1, dis2, dis3, dis4):
                comparer.type_cache.clear()
                assert comparer.distill(dis) == Distilled.invalid({})

    describe "issubclass":
        it "can say no for obviously incorrect things", Dis: Disassembler, comparer: strcs.disassemble.Comparer:

            class Thing:
                pass

            class Other:
                pass

            for a, b in [
                (str, int),
                (1, int),
                (int, 1),
                (int, dict),
                (Thing, int),
                (int, Thing),
                (Thing, Other),
            ]:
                assert not comparer.issubclass(a, b)
                assert not comparer.issubclass(Dis(a), b)
                assert not comparer.issubclass(a, Dis(b))
                assert not comparer.issubclass(Dis(a), Dis(b))
                assert not comparer.issubclass(tp.Union[Dis(a).checkable, None], Dis(b))
                assert not comparer.issubclass(
                    tp.Union[Dis(a).checkable, None], tp.Union[Dis(b).checkable, None]
                )
                assert not comparer.issubclass(Dis(a).checkable, tp.Union[Dis(b).checkable, None])

        it "match with generic vars", Dis: Disassembler, comparer: strcs.disassemble.Comparer:
            T = tp.TypeVar("T")
            U = tp.TypeVar("U")

            class Thing(tp.Generic[T, U]):
                pass

            class Other(tp.Generic[T, U], Thing[T, U]):
                pass

            class Another(tp.Generic[T, U]):
                pass

            class More(tp.Generic[T]):
                pass

            class Most(tp.Generic[T]):
                pass

            for comparing, comparing_to in [
                (Other, Thing),
                (Other[int, str], Thing[int, str]),
                (Other[int, str] | None, Thing[int, str]),
                (Other[bool, str], Thing[int, str]),
                (Thing[bool, str], Thing[int, str]),
                (Thing[int, str], Thing),
                (Thing[int | None, str], Thing),
                (Thing[int | None, str], Thing[int, str]),
                (Thing[int, str], Thing[int | None, str]),
                (Thing[tp.Annotated[bool, "asdf"], str], Thing[int, str]),
            ]:
                assert comparer.issubclass(comparing, comparing_to)
                assert comparer.issubclass(Dis(comparing), comparing_to)
                assert comparer.issubclass(Dis(comparing), Dis(comparing_to))
                assert comparer.issubclass(comparing, Dis(comparing_to))

                assert comparer.issubclass(Dis(comparing).checkable, Dis(comparing_to))
                assert comparer.issubclass(Dis(comparing), Dis(comparing_to).checkable)
                assert comparer.issubclass(Dis(comparing).checkable, Dis(comparing_to))
                assert comparer.issubclass(comparing, Dis(comparing_to).checkable)

            for comparing, comparing_to in [
                (Thing[tp.Annotated[int, "asdf"], str], Thing[bool, str]),
                (Other[str, str], Thing[int, str]),
                *[(Thing, other) for other in (Other, Another, More, Most)],
                *[(other, Thing) for other in (Another, More, Most)],
                (Thing[int, str], Other[int, str]),
                (Thing[int, str], Another[int, str]),
            ]:
                assert not comparer.issubclass(comparing, comparing_to)
                assert not comparer.issubclass(Dis(comparing), comparing_to)
                assert not comparer.issubclass(Dis(comparing), Dis(comparing_to))
                assert not comparer.issubclass(comparing, Dis(comparing_to))

                assert not comparer.issubclass(Dis(comparing).checkable, Dis(comparing_to))
                assert not comparer.issubclass(Dis(comparing), Dis(comparing_to).checkable)
                assert not comparer.issubclass(Dis(comparing).checkable, Dis(comparing_to))
                assert not comparer.issubclass(comparing, Dis(comparing_to).checkable)

    describe "isinstance":

        class IsInstanceAsserter(tp.Protocol):
            def __call__(
                self,
                val: object,
                typ: object,
                *,
                always_optional: bool = False,
                reverse: bool = False,
            ) -> None:
                ...

        @pytest.fixture
        def assertIsInstance(
            self,
            Dis: Disassembler,
            comparer: strcs.disassemble.Comparer,
        ) -> IsInstanceAsserter:
            def assertIsInstance(
                val: object, typ: object, *, always_optional: bool = False, reverse: bool = False
            ) -> None:
                def maybe_reverse(val: object) -> bool:
                    if reverse:
                        return not bool(val)
                    else:
                        return bool(val)

                assert maybe_reverse(comparer.isinstance(val, typ))
                assert (not comparer.isinstance(None, typ)) or always_optional

                round_one = [Dis(typ), Dis(typ).checkable]
                if isinstance(typ, type):
                    round_one.append(Dis(tp.Annotated[typ, "asdf"]))

                for dis in round_one:
                    assert maybe_reverse(comparer.isinstance(val, dis))
                    assert (not comparer.isinstance(None, dis)) or always_optional

                if not isinstance(typ, type):
                    return

                if typ in (None, type(None)):
                    return

                for dis in [
                    Dis(tp.Union[typ, None]),
                    Dis(tp.Annotated[tp.Union[typ, None], "asdf"]),
                    tp.Union[Dis(tp.Annotated[tp.Union[typ, None], "asdf"]).checkable, None],
                    tp.Union[Dis(tp.Annotated[typ, "asdf"]).checkable, None],
                ]:
                    assert maybe_reverse(comparer.isinstance(val, dis))
                    assert comparer.isinstance(None, dis)

            return assertIsInstance

        it "works on None", assertIsInstance: IsInstanceAsserter:
            assertIsInstance(None, type(None), always_optional=True)
            assertIsInstance(None, None, always_optional=True)

        it "works on simple types", assertIsInstance: IsInstanceAsserter:
            examples = [
                (1, int),
                ("asdf", str),
                (True, bool),
                (True, int),
                ({}, dict),
                ([], list),
                (set(), set),
            ]
            for val, typ in examples:
                assertIsInstance(val, typ)

        it "works on classes", assertIsInstance: IsInstanceAsserter:
            T = tp.TypeVar("T")

            class Thing(tp.Generic[T]):
                pass

            thing: Thing[int] = Thing()
            assertIsInstance(thing, Thing)
            assertIsInstance(thing, Thing[int])
            assertIsInstance(thing, Thing[str])

            class Other(tp.Generic[T], Thing[T]):
                pass

            assertIsInstance(thing, Other, reverse=True)
            assertIsInstance(thing, Other[int], reverse=True)
            assertIsInstance(thing, Other[str], reverse=True)

            other: Other[int] = Other()
            assertIsInstance(other, Other)
            assertIsInstance(other, Other[int])
            assertIsInstance(other, Other[str])

            other: Other[str] = Other()
            assertIsInstance(other, Other)
            assertIsInstance(other, Other[int])
            assertIsInstance(other, Other[str])

            class One:
                pass

            class Two:
                pass

            class Three(Two):
                pass

            class Four(Three):
                pass

            assertIsInstance(Four(), (One, Two, Three, Four))
            assertIsInstance(Four(), (int, str, bool, Four))
            assertIsInstance(Four(), (int, Two, bool))

            assertIsInstance(One(), int, reverse=True)
            assertIsInstance(One(), Two, reverse=True)
            assertIsInstance(One(), (Three, Four), reverse=True)
            assertIsInstance(One(), (Three, Four, One))
            assertIsInstance(One(), object, always_optional=True)

    describe "matches":

        @pytest.fixture
        def expander(
            self,
            Dis: Disassembler,
        ) -> Expander:
            def expander(
                checking: object, check_against: object
            ) -> Iterator[tuple[object, object, bool]]:
                if isinstance(checking, type):
                    checking_type = checking
                else:
                    checking_type = Dis(checking).checkable

                if isinstance(check_against, type):
                    check_against_type = check_against
                else:
                    check_against_type = Dis(check_against).checkable

                yield (
                    checking,
                    check_against,
                    False,
                )
                yield (
                    Dis(checking),
                    check_against,
                    False,
                )
                yield (
                    checking,
                    Dis(check_against),
                    False,
                )
                try:
                    hash(checking_type)
                except TypeError:
                    return

                if checking_type == () or isinstance(checking_type, str):
                    return

                try:
                    hash(check_against_type)
                except TypeError:
                    return

                yield (
                    checking,
                    tp.Union[check_against_type, None],
                    True,
                )
                yield (
                    tp.Annotated[Dis(checking).checkable, "asdf"],
                    tp.Union[check_against_type, None],
                    True,
                )
                yield (
                    Dis(tp.Annotated[checking_type, "asdf"]),
                    Dis(tp.Union[check_against_type, None]),
                    True,
                )
                yield (
                    Dis(tp.Annotated[checking_type, "asdf"]).checkable,
                    Dis(tp.Union[check_against_type, None]).checkable,
                    True,
                )
                yield (
                    Dis(Dis(tp.Annotated[checking_type, "asdf"]).checkable),
                    Dis(Dis(tp.Union[check_against_type, None]).checkable),
                    True,
                )

            return expander

        @pytest.fixture
        def assert_matches(
            self, expander: Expander, comparer: strcs.disassemble.Comparer
        ) -> MatchAsserter:
            def assert_matches(
                *checks: MatchCheck,
                subclasses: bool = False,
                allow_missing_typevars: bool = False,
            ) -> None:

                for check in checks:
                    attempts: list[tuple[object, object, bool, bool]] = []

                    for want in (check.orig, *check.matches):
                        for checking, check_against, optional in expander(want, check.orig):
                            attempts.append((checking, check_against, True, optional))
                    for want in check.not_match:
                        for checking, check_against, optional in expander(want, check.orig):
                            attempts.append((checking, check_against, False, optional))

                    for checking, check_against, match, optional in attempts:
                        if_error = "\n".join(
                            [
                                "",
                                f"subclasses={subclasses}, allow_missing_typevars={allow_missing_typevars}",
                                "" f"({type(checking)}) -->",
                                f"    {checking}",
                                f"({type(check_against)}) -->",
                                f"    {check_against}",
                            ]
                        )
                        if optional:
                            if not comparer.matches(
                                None,
                                check_against,
                                subclasses=subclasses,
                                allow_missing_typevars=allow_missing_typevars,
                            ):
                                raise AssertionError(if_error)
                        if match:
                            if not comparer.matches(
                                checking,
                                check_against,
                                subclasses=subclasses,
                                allow_missing_typevars=allow_missing_typevars,
                            ):
                                raise AssertionError(if_error)
                        else:
                            if comparer.matches(
                                checking,
                                check_against,
                                subclasses=subclasses,
                                allow_missing_typevars=allow_missing_typevars,
                            ):
                                raise AssertionError(if_error)

            return assert_matches

        describe "without subclasses":
            it "works on simple types", assert_matches: MatchAsserter:

                class Thing:
                    pass

                class Other(Thing):
                    pass

                assert_matches(
                    MatchCheck(
                        orig=int,
                        not_match=(dict,),
                    ),
                    MatchCheck(
                        orig=bool,
                        not_match=(list,),
                    ),
                    MatchCheck(
                        orig=dict,
                        not_match=(list,),
                    ),
                    MatchCheck(
                        orig=list,
                        not_match=(tuple,),
                    ),
                    MatchCheck(
                        orig=tuple,
                        not_match=(str,),
                    ),
                    MatchCheck(
                        orig=set,
                        not_match=(dict,),
                    ),
                    MatchCheck(
                        orig=str,
                        not_match=(int,),
                    ),
                    MatchCheck(
                        orig=Thing,
                        not_match=(Other,),
                    ),
                    MatchCheck(
                        orig=Other,
                        not_match=(Thing,),
                    ),
                    subclasses=False,
                )

            it "works for unions", assert_matches: MatchAsserter:

                class Thing:
                    pass

                class Other(Thing):
                    pass

                class MyStr(str):
                    pass

                assert_matches(
                    MatchCheck(
                        orig=int | str | Thing,
                        matches=(
                            int,
                            str,
                            Thing,
                            int | str,
                            int | Thing,
                        ),
                        not_match=(
                            dict,
                            bool,
                            MyStr,
                            MyStr(),
                        ),
                    ),
                    subclasses=False,
                )

            it "works on the type of the object rather than the object", assert_matches: MatchAsserter, type_cache:
                assert_matches(
                    MatchCheck(
                        orig=int,
                        matches=(1,),
                        not_match=("asdf",),
                    ),
                    MatchCheck(
                        orig=bool,
                        matches=(True,),
                        not_match=([],),
                    ),
                    MatchCheck(
                        orig=dict,
                        matches=({},),
                        not_match=([],),
                    ),
                    MatchCheck(
                        orig=list,
                        matches=([],),
                        not_match=({},),
                    ),
                    MatchCheck(
                        orig=tuple,
                        matches=((),),
                        not_match=(set(),),
                    ),
                    MatchCheck(
                        orig=set,
                        matches=(set(),),
                        not_match=(1,),
                    ),
                    MatchCheck(
                        orig=str,
                        matches=("",),
                        not_match=([],),
                    ),
                    subclasses=False,
                )

        describe "with subclasses":
            it "works on simple types", assert_matches: MatchAsserter:

                class Thing:
                    pass

                class Other(Thing):
                    pass

                assert_matches(
                    MatchCheck(
                        orig=bool,
                        matches=(
                            bool,
                            True,
                        ),
                        not_match=(
                            int,
                            list,
                            0,
                        ),
                    ),
                    MatchCheck(
                        orig=dict,
                        matches=(
                            dict,
                            OrderedDict,
                        ),
                        not_match=(list,),
                    ),
                    MatchCheck(
                        orig=Thing,
                        matches=(
                            Thing(),
                            Thing,
                            Other(),
                            Other,
                        ),
                        not_match=(set,),
                    ),
                    MatchCheck(
                        orig=Other,
                        matches=(
                            Other(),
                            Other,
                        ),
                        not_match=(set,),
                    ),
                    subclasses=True,
                )

            it "works for unions", assert_matches: MatchAsserter:

                class Thing:
                    pass

                class Other(Thing):
                    pass

                class MyStr(str):
                    pass

                assert_matches(
                    MatchCheck(
                        orig=int | str | Thing,
                        matches=(
                            int,
                            str,
                            Thing,
                            int | str,
                            int | Thing,
                            Other,
                            int | Other,
                            bool,
                            MyStr,
                            MyStr(),
                        ),
                        not_match=(
                            dict,
                            dict | MyStr,
                        ),
                    ),
                    subclasses=True,
                )

            it "works on the type of the object rather than the object", assert_matches: MatchAsserter:
                assert_matches(
                    MatchCheck(
                        orig=int,
                        matches=(1,),
                        not_match=("asdf",),
                    ),
                    MatchCheck(
                        orig=bool,
                        matches=(True,),
                        not_match=([],),
                    ),
                    MatchCheck(
                        orig=dict,
                        matches=(
                            {},
                            OrderedDict(),
                        ),
                        not_match=([],),
                    ),
                    MatchCheck(
                        orig=list,
                        matches=([],),
                        not_match=({},),
                    ),
                    MatchCheck(
                        orig=tuple,
                        matches=((),),
                        not_match=(set(),),
                    ),
                    MatchCheck(
                        orig=set,
                        matches=(set(),),
                        not_match=(1,),
                    ),
                    MatchCheck(
                        orig=str,
                        matches=("",),
                        not_match=([],),
                    ),
                    subclasses=True,
                )
