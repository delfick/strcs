# coding: spec

from strcs.base import NotSpecifiedMeta, CreateArgs
import strcs

from functools import partial
from unittest import mock
from attrs import define
import typing as tp
import cattrs
import pytest


@pytest.fixture()
def creg() -> strcs.CreateRegister:
    return strcs.CreateRegister()


@pytest.fixture()
def creator(creg) -> strcs.Creator:
    return partial(strcs.CreatorDecorator, creg)


class IsMeta:
    def __eq__(self, other):
        self.given = other
        return isinstance(other, strcs.Meta)

    def __repr__(self):
        if hasattr(self, "given"):
            if self == self.given:
                return repr(self.given)
            else:
                return f"<Given {type(self.given)}, expected a Meta>"
        return "<IsMeta?>"


class IsConverter:
    def __eq__(self, other):
        self.given = other
        return isinstance(other, cattrs.Converter)

    def __repr__(self):
        if hasattr(self, "given"):
            if self == self.given:
                return repr(self.given)
            else:
                return f"<Given {type(self.given)}, expected a Converter>"
        return "<IsConverter?>"


describe "Register":

    it "can register a convert function", creg: strcs.CreateRegister:

        @define
        class Thing:
            data: int

        @define
        class Stuff:
            info: str

        thing_maker = tp.cast(strcs.ConvertFunction, lambda args: {"data": 2})
        stuff_maker = tp.cast(strcs.ConvertFunction, lambda args: {"info": "hi"})

        assert creg.register == {}

        assert Thing not in creg
        creg[Thing] = thing_maker
        assert Thing in creg
        assert creg.register == {Thing: thing_maker}

        assert Stuff not in creg
        creg[Stuff] = stuff_maker
        assert Stuff in creg
        assert Thing in creg

        assert creg.register == {Thing: thing_maker, Stuff: stuff_maker}

    it "cannot register things that aren't types", creg: strcs.CreateRegister:

        class Thing:
            pass

        converter = mock.Mock(name="converter")
        creg[Thing] = converter
        assert creg.register == {Thing: converter}

        with pytest.raises(strcs.errors.CanOnlyRegisterTypes):
            creg[tp.cast(tp.Type, Thing())] = mock.Mock(name="nup")

    describe "can use the converters":
        it "works on anything", creg: strcs.CreateRegister:

            @define
            class Thing:
                pass

            thing = Thing()
            thing_maker = mock.Mock(name="thing_maker", return_value=thing)
            creg[Thing] = thing_maker
            assert creg.create(Thing) is thing
            thing_maker.assert_called_once_with(
                CreateArgs(strcs.NotSpecified, Thing, IsMeta(), IsConverter(), creg)
            )

            class Stuff:
                pass

            stuff = Stuff()
            stuff_maker = mock.Mock(name="stuff_maker", return_value=stuff)
            creg[Stuff] = stuff_maker
            assert creg.create(Stuff) is stuff
            stuff_maker.assert_called_once_with(
                CreateArgs(strcs.NotSpecified, Stuff, IsMeta(), IsConverter(), creg)
            )

        it "lets converter work on other types", creg: strcs.CreateRegister:

            @define
            class Other:
                name: str

            @define
            class Stuff:
                one: int
                two: int
                other: Other

            @define
            class Thing:
                number: int
                obj: Stuff

            thing_maker = mock.Mock(name="thing_maker")
            thing_maker.side_effect = lambda args: args.converter.structure_attrs_fromdict(
                args.value, args.want
            )
            creg[Thing] = thing_maker

            value = {"number": 20, "obj": {"one": 20, "two": 50, "other": {"name": "there"}}}
            made = creg.create(Thing, value)
            thing_maker.assert_called_once_with(
                CreateArgs(value, Thing, IsMeta(), IsConverter(), creg)
            )
            assert isinstance(made, Thing)
            assert made.number == 20
            assert isinstance(made.obj, Stuff)
            assert made.obj.one == 20
            assert made.obj.two == 50
            assert isinstance(made.obj.other, Other)
            assert made.obj.other.name == "there"

        it "let's us convert a type that isn't in the register", creg: strcs.CreateRegister:

            @define
            class Stuff:
                one: int
                two: int

            @define
            class Other:
                name: str
                stuff: Stuff

            stuff_maker = mock.Mock(name="stuff_maker")
            stuff_maker.side_effect = lambda args: args.converter.structure_attrs_fromdict(
                args.value, args.want
            )
            creg[Stuff] = stuff_maker

            value = {"name": "hi", "stuff": {"one": 45, "two": 76}}
            made = creg.create(Other, value)
            stuff_maker.assert_called_once_with(
                CreateArgs({"one": 45, "two": 76}, Stuff, IsMeta(), IsConverter(), creg)
            )
            assert isinstance(made, Other)
            assert made.name == "hi"
            assert isinstance(made.stuff, Stuff)
            assert made.stuff.one == 45
            assert made.stuff.two == 76

        it "doesn't recreate cattrs objects already created", creg: strcs.CreateRegister:

            @define
            class Stuff:
                one: int

            @define
            class Thing:
                stuff: Stuff

            creg[Thing] = lambda args: args.converter.structure_attrs_fromdict(
                args.value, args.want
            )

            stuff = Stuff(one=4)
            made = creg.create(Thing, {"stuff": stuff})
            assert isinstance(made, Thing)
            assert made.stuff is stuff

        it "still fails to recreate normal objects", creg: strcs.CreateRegister:

            class Stuff:
                def __init__(self, one: int):
                    self.one = one

            @define
            class Thing:
                stuff: Stuff

            creg[Thing] = lambda args: args.converter.structure_attrs_fromdict(
                args.value, args.want
            )

            stuff = Stuff(one=4)
            with pytest.raises(cattrs.errors.StructureHandlerNotFoundError):
                creg.create(Thing, {"stuff": stuff})

        it "let's us convert with super types", creg: strcs.CreateRegister:

            @define
            class Shape:
                three: int
                one: int = 1
                two: int = 2

            @define
            class Triangle(Shape):
                three: int
                one: int = 20
                two: int = 45

            @define
            class Square(Shape):
                three: int
                one: int = 33
                two: int = 22

            meta = strcs.Meta()
            meta["three"] = 100

            shape_maker = mock.Mock(name="shape_maker")
            shape_maker.side_effect = lambda args: args.converter.structure_attrs_fromdict(
                {"three": meta.retrieve_one(int, "three")}, args.want
            )
            creg[Shape] = shape_maker

            assert Square in creg
            assert Shape in creg
            assert Triangle in creg
            assert mock.Mock not in creg

            made = creg.create(Square, meta=meta)
            assert isinstance(made, Square)
            assert made.one == 33
            assert made.two == 22
            assert made.three == 100
            shape_maker.assert_called_once_with(
                CreateArgs(strcs.NotSpecified, Square, meta, IsConverter(), creg)
            )
            shape_maker.reset_mock()

            made = creg.create(Triangle, meta=meta)
            assert isinstance(made, Triangle)
            assert made.one == 20
            assert made.two == 45
            assert made.three == 100
            shape_maker.assert_called_once_with(
                CreateArgs(strcs.NotSpecified, Triangle, meta, IsConverter(), creg)
            )
            shape_maker.reset_mock()

            made = creg.create(Shape, meta=meta)
            assert isinstance(made, Shape)
            assert made.one == 1
            assert made.two == 2
            assert made.three == 100
            shape_maker.assert_called_once_with(
                CreateArgs(strcs.NotSpecified, Shape, meta, IsConverter(), creg)
            )
            shape_maker.reset_mock()

        it "doesn't fail on checking against a not type in the register", creg: strcs.CreateRegister:

            @define
            class Thing:
                pass

            assert Thing not in creg
            assert tp.cast(tp.Type, Thing()) not in creg

            creg[Thing] = tp.cast(strcs.ConvertFunction, mock.Mock(name="creator"))
            assert Thing in creg
            assert tp.cast(tp.Type, Thing()) not in creg

describe "Creators":
    it "stores the type and the register", creator: strcs.Creator, creg: strcs.CreateRegister:

        class Thing:
            pass

        dec = creator(Thing)
        assert dec.typ is Thing
        assert dec.register is creg

    it "takes a ConvertDefinition", creator: strcs.Creator:

        class Thing:
            pass

        thing = Thing()

        dec = creator(Thing)
        assert not hasattr(dec, "func")

        make = mock.Mock(name="make", side_effect=lambda: thing)
        decorated = dec(make)

        assert decorated is make
        assert dec.func is make

        assert dec.register.create(Thing) is thing
        make.assert_called_once_with()

    it "can work on things that aren't attrs classes", creator: strcs.Creator, creg: strcs.CreateRegister:

        @define(frozen=True)
        class Info(strcs.MergedAnnotation):
            multiple: int

        def multiply(val: int, /, multiple: int):
            return val * multiple

        assert creg.create(tp.Annotated[int, strcs.Ann(Info(multiple=2), multiply)], 3) == 6

        @define
        class Thing:
            thing: tp.Annotated[int, strcs.Ann(Info(multiple=5), multiply)]

        assert creg.create(Thing, {"thing": 20}).thing == 100

    describe "invoking function":
        it "calls func if it has no arguments", creator: strcs.Creator, creg: strcs.CreateRegister:
            called = []

            class Thing:
                pass

            thing = Thing()

            @creator(Thing)
            def make() -> strcs.ConvertResponse[Thing]:
                called.append(1)
                return thing

            assert creg.create(Thing) is thing
            assert called == [1]

        it "calls the func with the value if we ask for value", creator: strcs.Creator, creg: strcs.CreateRegister:
            called = []

            class Thing:
                pass

            thing = Thing()

            @creator(Thing, assume_unchanged_converted=False)
            def make(value: tp.Any) -> strcs.ConvertResponse[Thing]:
                called.append(value)
                return thing

            assert creg.create(Thing) is thing
            assert called == [strcs.NotSpecified]

            assert creg.create(Thing, 1) is thing
            assert called == [strcs.NotSpecified, 1]

            assert creg.create(Thing, {"one": 2}) is thing
            assert called == [strcs.NotSpecified, 1, {"one": 2}]

            assert creg.create(Thing, thing) is thing
            assert called == [strcs.NotSpecified, 1, {"one": 2}, thing]

        it "calls the func with the value and type if we ask for value and type", creator: strcs.Creator, creg: strcs.CreateRegister:
            called = []

            class Thing:
                pass

            thing = Thing()

            @creator(Thing, assume_unchanged_converted=False)
            def make(value: tp.Any, want: tp.Type, /) -> strcs.ConvertResponse[Thing]:
                called.append((value, want))
                return thing

            assert creg.create(Thing) is thing
            assert called == [(strcs.NotSpecified, Thing)]

            assert creg.create(Thing, 1) is thing
            assert called == [(strcs.NotSpecified, Thing), (1, Thing)]

            assert creg.create(Thing, {"one": 2}) is thing
            assert called == [(strcs.NotSpecified, Thing), (1, Thing), ({"one": 2}, Thing)]

            assert creg.create(Thing, thing) is thing
            assert called == [
                (strcs.NotSpecified, Thing),
                (1, Thing),
                ({"one": 2}, Thing),
                (thing, Thing),
            ]

            @define
            class Child(Thing):
                pass

            assert creg.create(Child, thing) is thing
            assert called == [
                (strcs.NotSpecified, Thing),
                (1, Thing),
                ({"one": 2}, Thing),
                (thing, Thing),
                (thing, Child),
            ]

        it "calls function with information from meta if it asks for it", creator: strcs.Creator, creg: strcs.CreateRegister:
            called = []

            class Thing:
                pass

            thing = Thing()

            @creator(Thing)
            def make(
                value: tp.Any, want: tp.Type, /, number: int, specific: Thing
            ) -> strcs.ConvertResponse[Thing]:
                called.append((value, want, number, specific))
                return thing

            meta = strcs.Meta()
            meta["one"] = 1
            meta["specific"] = thing

            assert creg.create(Thing, meta=meta) is thing
            assert called == [(strcs.NotSpecified, Thing, 1, thing)]

            @define
            class Child(Thing):
                pass

            child = Child()
            del meta["one"]
            meta["number"] = 30
            meta["specific"] = child

            called.clear()
            assert creg.create(Thing, meta=meta) is thing
            assert called == [(strcs.NotSpecified, Thing, 30, child)]

        it "can use a default value for things asked for from meta", creator: strcs.Creator, creg: strcs.CreateRegister:

            @define
            class Thing:
                val: str

            @creator(Thing)
            def create_thing(
                val: str,
                /,
                prefix: str,
                suffix: str = "there",
                super_prefix: str = "blah",
                non_typed="meh",
            ):
                return {"val": f"{prefix}:{val}:{suffix}:{super_prefix}:{non_typed}"}

            meta = strcs.Meta()
            meta["prefix"] = "pref"
            assert creg.create(Thing, "hello", meta=meta).val == "pref:hello:there:blah:meh"
            assert (
                creg.create(
                    Thing, "hello", meta=meta.clone(data_extra={"non_typed": "laksjdfl"})
                ).val
                == "pref:hello:there:blah:laksjdfl"
            )
            assert (
                creg.create(Thing, "hello", meta=meta.clone(data_extra={"suffix": "hi"})).val
                == "pref:hello:hi:blah:meh"
            )

        it "can get annotated data from class definition into meta", creator: strcs.Creator, creg: strcs.CreateRegister:

            @define(frozen=True)
            class SentenceAnnotation(strcs.Annotation):
                prefix: str

            @define
            class Sentence:
                sentence: str

            @define
            class Thing:
                one: tp.Annotated[Sentence, SentenceAnnotation(prefix="hello")]

            @creator(Sentence)
            def create_sentence(val: str | tp.Dict, /, ann: SentenceAnnotation, suffix: str):
                return {"sentence": ann.prefix + val + suffix}

            meta = strcs.Meta()
            meta["suffix"] = " mate"
            assert (
                creg.create(Thing, {"one": " there"}, meta=meta).one.sentence == "hello there mate"
            )

        it "can get data spread into meta", creator: strcs.Creator, creg: strcs.CreateRegister:

            @define(frozen=True)
            class ChildAnnotation(strcs.MergedAnnotation):
                two: int

            @define(frozen=True)
            class ThingAnnotation(strcs.MergedAnnotation):
                one: int

            @define
            class Child:
                data: int

            @define
            class Thing:
                child: tp.Annotated[Child, ChildAnnotation(two=30)]

            @define
            class Overall:
                thing: tp.Annotated[Thing, ThingAnnotation(one=40)]

            @creator(Child)
            def create_thing(val: int, /, one: int, two: int):
                return {"data": val + one + two}

            assert creg.create(Overall, {"thing": {"child": 3}}).thing.child.data == 73
            assert creg.create(Overall, {"thing": {"child": 10}}).thing.child.data == 80

        it "can convert lists one thing at a time", creator: strcs.Creator, creg: strcs.CreateRegister:

            counts = {"upto": 0}

            @define
            class Thing:
                one: int
                upto: int

            @define
            class Things:
                things: list[Thing]

            @creator(Thing)
            def create_thing(one: int):
                counts["upto"] += 1
                return {"one": one, "upto": counts["upto"]}

            made = creg.create(Things, {"things": [4, 5, 6]})
            assert isinstance(made, Things)

            assert [(t.one, t.upto) for t in made.things] == [(4, 1), (5, 2), (6, 3)]

        it "can adjust meta from a method on the annotation", creator: strcs.Creator, creg: strcs.CreateRegister:
            """Entirely possible I got a bit carried away with this example and I agree this is a stupid way of whatever this is"""

            @define(frozen=True)
            class LottoAnnotation(strcs.Annotation):
                numbers: tp.Tuple[int, int, int, int, int]

                def adjusted_meta(self, meta: strcs.Meta, typ: tp.Type) -> strcs.Meta:
                    return meta.clone(
                        data_extra={"powerball": self.numbers[-1], "numbers": self.numbers[:-1]}
                    )

            @define
            class Result:
                winner: bool

            @define
            class Ticket:
                numbers: list[int]
                powerball: int

            @define
            class Lotto:
                results: tp.Annotated[list[Result], LottoAnnotation(numbers=(2, 6, 8, 10, 69))]

            @creator(Result)
            def create_result(
                val: Ticket, /, numbers: tp.Tuple, powerball: int
            ) -> strcs.ConvertResponse:
                return {"winner": val.numbers == list(numbers) and val.powerball == powerball}

            lotto = creg.create(
                Lotto,
                {
                    "results": [
                        Ticket(numbers=[1, 2, 3, 4], powerball=2),
                        Ticket(numbers=[2, 6, 8, 10], powerball=22),
                        Ticket(numbers=[2, 6, 8, 10], powerball=69),
                        Ticket(numbers=[5, 8, 4, 3], powerball=3),
                    ]
                },
            )

            assert lotto.results == [
                Result(winner=False),
                Result(winner=False),
                Result(winner=True),
                Result(winner=False),
            ]

        it "can override a creator in the annotation", creator: strcs.Creator, creg: strcs.CreateRegister:

            @define
            class Thing:
                val: int

            @creator(Thing)
            def create_thing(val: int) -> strcs.ConvertResponse:
                return {"val": val * 2}

            @define
            class Things:
                thing1: Thing
                thing2: tp.Annotated[Thing, lambda val: {"val": val * 3}]
                thing3: Thing

            things = creg.create(Things, {"thing1": 1, "thing2": 5, "thing3": 10})
            assert isinstance(things, Things)
            assert things.thing1.val == 2
            assert things.thing2.val == 15
            assert things.thing3.val == 20

        it "can override a creator and meta in the annotation", creator: strcs.Creator, creg: strcs.CreateRegister:

            @define(frozen=True)
            class ThingAnnotation(strcs.MergedAnnotation):
                add: int

            @define
            class Thing:
                val: int

            @creator(Thing)
            def create_thing(val: int) -> strcs.ConvertResponse:
                return {"val": val * 2}

            def other_creator(val: int, /, add: int) -> strcs.ConvertResponse:
                return {"val": val + add}

            @define
            class Things:
                thing1: Thing
                thing2: tp.Annotated[Thing, strcs.Ann(ThingAnnotation(add=20), other_creator)]
                thing3: Thing

            things = creg.create(Things, {"thing1": 1, "thing2": 5, "thing3": 10})
            assert isinstance(things, Things)
            assert things.thing1.val == 2
            assert things.thing2.val == 25
            assert things.thing3.val == 20

        it "can use an annotation to get something from meta", creator: strcs.Creator, creg: strcs.CreateRegister:

            class Other:
                pass

            other = Other()

            @define
            class Thing:
                want: tp.Annotated[Other, strcs.FromMeta("other")]

            assert creg.create(Thing, meta=strcs.Meta(data={"o": other})).want is other
            assert creg.create(Thing, meta=strcs.Meta(data={"other": other})).want is other

            with pytest.raises(strcs.errors.NoDataByTypeName):
                assert creg.create(Thing).want is other

    describe "interpreting the response":
        it "raises exception if we get None", creator: strcs.Creator, creg: strcs.CreateRegister:
            called = []

            class Thing:
                pass

            @creator(Thing)
            def make() -> strcs.ConvertResponse[Thing]:
                called.append(1)
                return None

            with pytest.raises(strcs.errors.UnableToConvert):
                creg.create(Thing)
            assert called == [1]

        it "returns the result if the result is of the correct type", creator: strcs.Creator, creg: strcs.CreateRegister:
            called = []

            class Thing:
                pass

            thing = Thing()

            @creator(Thing)
            def make() -> strcs.ConvertResponse[Thing]:
                called.append(1)
                return thing

            assert creg.create(Thing) is thing
            assert called == [1]

        it "returns the value created with if the result is True and value is not NotSpecified", creator: strcs.Creator, creg: strcs.CreateRegister:
            called = []

            class Thing:
                pass

            thing1 = Thing()
            thing2 = Thing()
            thing3 = Thing()

            @creator(Thing, assume_unchanged_converted=False)
            def make() -> strcs.ConvertResponse[Thing]:
                called.append(1)
                return True

            with pytest.raises(strcs.errors.UnableToConvert):
                creg.create(Thing)
            assert called == [1]

            assert creg.create(Thing, thing1) is thing1
            assert called == [1, 1]

            assert creg.create(Thing, thing2) is thing2
            assert called == [1, 1, 1]

            assert creg.create(Thing, thing3) is thing3
            assert called == [1, 1, 1, 1]

        it "returns the value as is without going through function if assume unchanged and value is of the same type", creator: strcs.Creator, creg: strcs.CreateRegister:
            called = []

            @define
            class Thing:
                pass

            thing = Thing()

            @creator(Thing)
            def make(thing: Thing | tp.Dict) -> strcs.ConvertResponse:
                called.append(1)
                return thing

            assert creg.create(Thing, thing) is thing
            assert called == []

            got = creg.create(Thing, {})
            assert isinstance(got, Thing)
            assert got is not thing
            assert called == [1]

            class Child(Thing):
                pass

            child = Child()

            assert creg.create(Thing, child) is child
            assert called == [1]

        it "can use NotSpecified if the type we want is that and we return True", creator: strcs.Creator, creg: strcs.CreateRegister:
            called = []

            @creator(NotSpecifiedMeta, assume_unchanged_converted=False)
            def make() -> strcs.ConvertResponse[NotSpecifiedMeta]:
                called.append(1)
                return True

            assert creg.create(NotSpecifiedMeta) is strcs.NotSpecified
            assert called == [1]

        it "turns a dictionary into the object", creator: strcs.Creator, creg: strcs.CreateRegister:
            called = []

            @define
            class Thing:
                one: int
                two: str

            @creator(Thing)
            def make() -> strcs.ConvertResponse[NotSpecifiedMeta]:
                called.append(1)
                return {"one": 3, "two": "twenty"}

            made = creg.create(Thing)
            assert isinstance(made, Thing)
            assert made.one == 3
            assert made.two == "twenty"
            assert called == [1]

        it "uses creator for other registered classes", creator: strcs.Creator, creg: strcs.CreateRegister:
            called = []

            @define
            class Other:
                three: int
                four: int

            @creator(Other)
            def make() -> strcs.ConvertResponse[Other]:
                called.append(2)
                return {"three": 20, "four": 50}

            @define
            class Stuff:
                five: int = 1
                six: int = 2

            @define
            class Thing:
                one: int
                two: str
                other1: Other
                other2: Other
                stuff: Stuff

            @creator(Thing)
            def make2() -> strcs.ConvertResponse[NotSpecifiedMeta]:
                called.append(1)
                return {"one": 3, "two": "twenty", "stuff": {}, "other1": {}}

            made = creg.create(Thing)
            assert isinstance(made, Thing)
            assert made.one == 3
            assert made.two == "twenty"
            assert isinstance(made.other1, Other)
            assert made.other1.three == 20
            assert made.other1.four == 50
            assert isinstance(made.other2, Other)
            assert made.other2.three == 20
            assert made.other2.four == 50
            assert isinstance(made.stuff, Stuff)
            assert made.stuff.five == 1
            assert made.stuff.six == 2
            assert called == [1, 2, 2]

        it "can have a creator with no function", creator: strcs.Creator, creg: strcs.CreateRegister:

            @define
            class Thing:
                one: int = 1

            creator(Thing)()

            made = creg.create(Thing)
            assert isinstance(made, Thing)
            assert made.one == 1

            thing = Thing(one=2)
            assert creg.create(Thing, thing) is thing

            made = creg.create(Thing, {"one": 20})
            assert isinstance(made, Thing)
            assert made.one == 20

            @define
            class Other:
                pass

            for nope in (0, 1, False, True, [], [1], lambda: 1, Other, Other(), Thing):
                with pytest.raises(strcs.errors.UnableToConvert):
                    creg.create(Thing, nope)

        describe "generator creator":
            it "can modify the created object inside the creator", creator: strcs.Creator, creg: strcs.CreateRegister:

                @define(slots=False)
                class Thing:
                    one: int

                    def __post_attrs_init__(self):
                        self.two = None

                @creator(Thing)
                def make(value: tp.Any):
                    made = yield value
                    made.two = 2
                    yield True

                made = creg.create(Thing, {"one": 20})
                assert isinstance(made, Thing)
                assert made.one == 20
                assert made.two == 2

            it "can modify the created object inside the creator without yielding second time", creator: strcs.Creator, creg: strcs.CreateRegister:

                @define(slots=False)
                class Thing:
                    one: int

                    def __post_attrs_init__(self):
                        self.two = None

                @creator(Thing)
                def make(value: tp.Any):
                    made = yield value
                    made.two = 2

                made = creg.create(Thing, {"one": 20})
                assert isinstance(made, Thing)
                assert made.one == 20
                assert made.two == 2

            it "considers not yielding means it could not convert", creator: strcs.Creator, creg: strcs.CreateRegister:

                @define(slots=False)
                class Thing:
                    one: int

                @creator(Thing)
                def make(value: tp.Any):
                    if False:
                        yield value

                with pytest.raises(strcs.errors.UnableToConvert):
                    creg.create(Thing, {"one": 20})

            it "uses the first yielded thing to determine what is made", creator: strcs.Creator, creg: strcs.CreateRegister:

                @define(slots=False)
                class Thing:
                    one: int = 1

                @creator(Thing)
                def make(value: tp.Any):
                    yield value

                made = creg.create(Thing, {"one": 20})
                assert isinstance(made, Thing)
                assert made.one == 20

                made = creg.create(Thing)
                assert isinstance(made, Thing)
                assert made.one == 1

                thing = Thing(one=4)
                made = creg.create(Thing, thing)
                assert made is thing

            it "can yield another generator because recursion is fun", creator: strcs.Creator, creg: strcs.CreateRegister:
                called = []

                @define(slots=False)
                class Thing:
                    one: int = 1

                    def __post_attrs_init__(self):
                        self.two = None
                        self.three = None

                def recursion_is_fun(value: tp.Any):
                    assert isinstance(value, dict)
                    assert value == {"one": 20}
                    called.append(2)
                    made = yield {"one": 60}
                    made.two = 500
                    called.append(3)

                @creator(Thing)
                def make(value: tp.Any):
                    called.append(1)
                    made = yield recursion_is_fun(value)
                    made.three = 222
                    called.append(4)

                made = creg.create(Thing, {"one": 20})
                assert isinstance(made, Thing)
                assert made.one == 60
                assert made.two == 500
                assert made.three == 222

            it "uses what is yielded the second time", creator: strcs.Creator, creg: strcs.CreateRegister:

                @define(slots=False)
                class Thing:
                    one: int = 1

                @creator(Thing)
                def make(value: tp.Any):
                    made = yield {"one": 0}
                    assert isinstance(made, Thing)
                    assert made.one == 0
                    yield value

                made = creg.create(Thing, {"one": 20})
                assert isinstance(made, Thing)
                assert made.one == 20

                made = creg.create(Thing)
                assert isinstance(made, Thing)
                assert made.one == 1

                thing = Thing(one=4)
                made = creg.create(Thing, thing)
                assert made is thing
