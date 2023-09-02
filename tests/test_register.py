# coding: spec

import secrets
import typing as tp
from unittest import mock

import cattrs
import pytest
from attrs import define

import strcs


@pytest.fixture(params=(True, False), ids=("with_cache", "without_cache"))
def creg(request: pytest.FixtureRequest) -> strcs.CreateRegister:
    if request.param:
        return strcs.CreateRegister()
    else:

        class Cache(strcs.TypeCache):
            def __setitem__(self, k: object, v: strcs.Type) -> None:
                return

        return strcs.CreateRegister(type_cache=Cache())


@pytest.fixture()
def creator(creg: strcs.CreateRegister) -> strcs.Creator:
    return creg.make_decorator()


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

    @classmethod
    def test(kls) -> strcs.Meta:
        return tp.cast(strcs.Meta, kls())


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

    @classmethod
    def test(kls) -> cattrs.Converter:
        return tp.cast(cattrs.Converter, kls())


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
        assert creg.register == {strcs.Type.create(Thing, cache=creg.type_cache): thing_maker}

        assert Stuff not in creg
        creg[Stuff] = stuff_maker
        assert Stuff in creg
        assert Thing in creg

        assert creg.register == {
            strcs.Type.create(Thing, cache=creg.type_cache): thing_maker,
            strcs.Type.create(Stuff, cache=creg.type_cache): stuff_maker,
        }

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
                strcs.CreateArgs(
                    strcs.NotSpecified,
                    strcs.Type.create(Thing, cache=creg.type_cache),
                    IsMeta.test(),
                    IsConverter.test(),
                    creg,
                )
            )

            class Stuff:
                pass

            stuff = Stuff()
            stuff_maker = mock.Mock(name="stuff_maker", return_value=stuff)
            creg[Stuff] = stuff_maker
            assert creg.create(Stuff) is stuff
            stuff_maker.assert_called_once_with(
                strcs.CreateArgs(
                    strcs.NotSpecified,
                    strcs.Type.create(Stuff, cache=creg.type_cache),
                    IsMeta.test(),
                    IsConverter.test(),
                    creg,
                )
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
                args.value, args.want.extracted
            )
            creg[Thing] = thing_maker

            value = {"number": 20, "obj": {"one": 20, "two": 50, "other": {"name": "there"}}}
            made = creg.create(Thing, value)
            thing_maker.assert_called_once_with(
                strcs.CreateArgs(
                    value,
                    strcs.Type.create(Thing, cache=creg.type_cache),
                    IsMeta.test(),
                    IsConverter.test(),
                    creg,
                )
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
                args.value, args.want.extracted
            )
            creg[Stuff] = stuff_maker

            value = {"name": "hi", "stuff": {"one": 45, "two": 76}}
            made = creg.create(Other, value)
            stuff_maker.assert_called_once_with(
                strcs.CreateArgs(
                    {"one": 45, "two": 76},
                    strcs.Type.create(Stuff, cache=creg.type_cache),
                    IsMeta.test(),
                    IsConverter.test(),
                    creg,
                )
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

            def creator(args: strcs.CreateArgs[Thing]) -> Thing:
                assert isinstance(args.value, dict)
                return args.converter.structure_attrs_fromdict(
                    args.value, args.want.checkable_as_type
                )

            creg[Thing] = creator

            stuff = Stuff(one=4)
            made = creg.create(Thing, {"stuff": stuff})
            assert isinstance(made, Thing)
            assert made.stuff is stuff

        it "can recreate normal objects", creg: strcs.CreateRegister:

            class Stuff:
                def __init__(self, one: int):
                    self.one = one

            @define
            class Thing:
                stuff: Stuff

            def creator(args: strcs.CreateArgs[Thing]) -> Thing:
                assert isinstance(args.value, dict)
                return args.converter.structure_attrs_fromdict(
                    args.value, args.want.checkable_as_type
                )

            creg[Thing] = creator

            stuff = Stuff(one=4)
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

            meta = creg.meta()
            meta["three"] = 100

            shape_maker = mock.Mock(name="shape_maker")
            shape_maker.side_effect = lambda args: args.converter.structure_attrs_fromdict(
                {"three": meta.retrieve_one(int, "three", type_cache=creg.type_cache)},
                args.want.extracted,
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
                strcs.CreateArgs(
                    strcs.NotSpecified,
                    strcs.Type.create(Square, cache=creg.type_cache),
                    meta,
                    IsConverter.test(),
                    creg,
                )
            )
            shape_maker.reset_mock()

            tri = creg.create(Triangle, meta=meta)
            assert isinstance(tri, Triangle)
            assert tri.one == 20
            assert tri.two == 45
            assert tri.three == 100
            shape_maker.assert_called_once_with(
                strcs.CreateArgs(
                    strcs.NotSpecified,
                    strcs.Type.create(Triangle, cache=creg.type_cache),
                    meta,
                    IsConverter.test(),
                    creg,
                )
            )
            shape_maker.reset_mock()

            shape = creg.create(Shape, meta=meta)
            assert isinstance(shape, Shape)
            assert shape.one == 1
            assert shape.two == 2
            assert shape.three == 100
            shape_maker.assert_called_once_with(
                strcs.CreateArgs(
                    strcs.NotSpecified,
                    strcs.Type.create(Shape, cache=creg.type_cache),
                    meta,
                    IsConverter.test(),
                    creg,
                )
            )
            shape_maker.reset_mock()

        it "fails on checking against a not type in the register", creg: strcs.CreateRegister:

            @define
            class Thing:
                pass

            assert Thing not in creg
            with pytest.raises(ValueError, match="Can only check against types or Type instances"):
                assert tp.cast(type, Thing()) not in creg

            creg[Thing] = tp.cast(strcs.ConvertFunction, mock.Mock(name="creator"))
            assert Thing in creg
            with pytest.raises(ValueError, match="Can only check against types or Type instances"):
                assert tp.cast(type, Thing()) not in creg

describe "Creators":
    it "stores the type and the register", creator: strcs.Creator, creg: strcs.CreateRegister:

        class Thing:
            pass

        dec = tp.cast(strcs.CreatorDecorator, creator(Thing))
        assert dec.original is Thing
        assert dec.register is creg

    it "takes a ConvertDefinition", creator: strcs.Creator:

        class Thing:
            pass

        thing = Thing()

        dec = creator(Thing)
        assert not hasattr(dec, "func")

        make = mock.Mock(name="make", side_effect=lambda: thing)
        decorated = dec(tp.cast(strcs.ConvertDefinition[Thing], make))

        assert decorated is make
        assert tp.cast(strcs.CreatorDecorator, dec).func is make

        assert tp.cast(strcs.CreatorDecorator, dec).register.create(Thing) is thing
        make.assert_called_once_with()

    it "can be given as an override in an annotation", creator: strcs.Creator, creg: strcs.CreateRegister:

        @define(frozen=True)
        class Info(strcs.MergedMetaAnnotation):
            multiple: int

        def multiply(value: object, /, multiple: int) -> int | None:
            if not isinstance(value, int):
                return None
            return value * multiple

        assert creg.create_annotated(int, strcs.Ann(Info(multiple=2), multiply), 3) == 6

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
            def make() -> Thing:
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
            def make(value: object) -> Thing:
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
            def make(value: object, want: strcs.Type, /) -> Thing:
                called.append((value, want.extracted))
                if not isinstance(value, Thing):
                    return thing
                return value

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

            child = Child()
            assert creg.create(Child, child) is child
            assert called == [
                (strcs.NotSpecified, Thing),
                (1, Thing),
                ({"one": 2}, Thing),
                (thing, Thing),
                (child, Child),
            ]

            with pytest.raises(strcs.errors.SupertypeNotValid) as e:
                creg.create(Child, thing)

            assert e.value.got == Thing
            assert e.value.want == Child

        it "calls function with information from meta if it asks for it", creator: strcs.Creator, creg: strcs.CreateRegister:
            called = []

            class Thing:
                pass

            thing = Thing()

            @creator(Thing)
            def make(value: object, want: strcs.Type, /, number: int, specific: Thing) -> Thing:
                called.append((value, want.extracted, number, specific))
                return thing

            meta = creg.meta()
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
                value: str,
                /,
                prefix: str,
                suffix: str = "there",
                super_prefix: str = "blah",
                non_typed="meh",
            ):
                return {"val": f"{prefix}:{value}:{suffix}:{super_prefix}:{non_typed}"}

            meta = creg.meta()
            meta["prefix"] = "pref"
            assert creg.create(Thing, "hello", meta=meta).val == "pref:hello:there:blah:meh"
            assert (
                creg.create(Thing, "hello", meta=meta.clone({"non_typed": "laksjdfl"})).val
                == "pref:hello:there:blah:laksjdfl"
            )
            assert (
                creg.create(Thing, "hello", meta=meta.clone({"suffix": "hi"})).val
                == "pref:hello:hi:blah:meh"
            )

        it "can get annotated data from class definition into meta", creator: strcs.Creator, creg: strcs.CreateRegister:

            @define(frozen=True)
            class SentenceAnnotation(strcs.MetaAnnotation):
                prefix: str

            @define
            class Sentence:
                sentence: str

            @define
            class Thing:
                one: tp.Annotated[Sentence, SentenceAnnotation(prefix="hello")]

            @creator(Sentence)
            def create_sentence(
                value: object, /, ann: SentenceAnnotation, suffix: str
            ) -> dict | None:
                if not isinstance(value, str):
                    return None
                return {"sentence": ann.prefix + value + suffix}

            meta = creg.meta()
            meta["suffix"] = " mate"
            assert (
                creg.create(Thing, {"one": " there"}, meta=meta).one.sentence == "hello there mate"
            )

        it "can get data spread into meta", creator: strcs.Creator, creg: strcs.CreateRegister:

            @define(frozen=True)
            class ChildAnnotation(strcs.MergedMetaAnnotation):
                two: int

            @define(frozen=True)
            class ThingAnnotation(strcs.MergedMetaAnnotation):
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
            def create_thing(value: int, /, one: int, two: int):
                return {"data": value + one + two}

            assert creg.create(Overall, {"thing": {"child": 3}}).thing.child.data == 73
            assert creg.create(Overall, {"thing": {"child": 10}}).thing.child.data == 80

        it "can not add optional fields to the meta when they are none", creator: strcs.Creator, creg: strcs.CreateRegister:

            @define(frozen=True)
            class Annotation(strcs.MergedMetaAnnotation):
                one: int = 3
                two: str | None = None

            @define
            class Thing:
                val: str

            @creator(Thing)
            def create_thing(value: object, /, one: int = 0, two: str = "asdf") -> dict | None:
                if not isinstance(value, str):
                    return None
                return {"val": f"{value}|{one}|{two}"}

            assert creg.create_annotated(Thing, Annotation(one=1), "hi").val == "hi|1|asdf"
            assert (
                creg.create_annotated(Thing, Annotation(one=1, two="stuff"), "hi").val
                == "hi|1|stuff"
            )
            assert creg.create_annotated(Thing, Annotation(two="stuff"), "hi").val == "hi|3|stuff"
            assert creg.create_annotated(Thing, Annotation(), "hi").val == "hi|3|asdf"
            assert creg.create(Thing, "hi").val == "hi|0|asdf"

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
            def create_thing(value: object) -> dict | None:
                if not isinstance(value, int):
                    return None
                counts["upto"] += 1
                return {"one": value, "upto": counts["upto"]}

            made = creg.create(Things, {"things": [4, 5, 6]})
            assert isinstance(made, Things)

            assert [(t.one, t.upto) for t in made.things] == [(4, 1), (5, 2), (6, 3)]

        it "can adjust meta from a method on the annotation", creator: strcs.Creator, creg: strcs.CreateRegister:
            """Entirely possible I got a bit carried away with this example and I agree this is a stupid way of whatever this is"""

            @define(frozen=True)
            class LottoAnnotation(strcs.MetaAnnotation):
                numbers: tuple[int, int, int, int, int]

                def adjusted_meta(
                    self, meta: strcs.Meta, typ: type, type_cache: strcs.TypeCache
                ) -> strcs.Meta:
                    return meta.clone({"powerball": self.numbers[-1], "numbers": self.numbers[:-1]})

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
            def create_result(value: object, /, numbers: tuple, powerball: int) -> dict | None:
                if not isinstance(value, Ticket):
                    return None
                return {"winner": value.numbers == list(numbers) and value.powerball == powerball}

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
            def create_thing(value: object) -> dict | None:
                if not isinstance(value, int):
                    return None
                return {"val": value * 2}

            @define
            class Things:
                thing1: Thing
                thing2: tp.Annotated[Thing, lambda value: {"val": value * 3}]
                thing3: Thing

            things = creg.create(Things, {"thing1": 1, "thing2": 5, "thing3": 10})
            assert isinstance(things, Things)
            assert things.thing1.val == 2
            assert things.thing2.val == 15
            assert things.thing3.val == 20

        it "can override a creator and meta in the annotation", creator: strcs.Creator, creg: strcs.CreateRegister:

            @define(frozen=True)
            class ThingAnnotation(strcs.MergedMetaAnnotation):
                add: int

            @define
            class Thing:
                val: int

            @creator(Thing)
            def create_thing(value: object) -> dict | None:
                if not isinstance(value, int):
                    return None
                return {"val": value * 2}

            def other_creator(value: object, /, add: int) -> dict | None:
                if not isinstance(value, int):
                    return None
                return {"val": value + add}

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

            assert creg.create(Thing, meta=creg.meta({"o": other})).want is other
            assert creg.create(Thing, meta=creg.meta({"other": other})).want is other

            with pytest.raises(strcs.errors.NoDataByTypeName):
                assert creg.create(Thing).want is other

    describe "interpreting the response":
        it "raises exception if we get None", creator: strcs.Creator, creg: strcs.CreateRegister:
            called = []

            class Thing:
                pass

            @creator(Thing)
            def make() -> None:
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
            def make() -> Thing:
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
            def make() -> bool:
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
            def make(thing: object) -> Thing | dict | None:
                called.append(1)
                if not isinstance(thing, (Thing, dict)):
                    return None
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

            @creator(strcs.NotSpecifiedMeta, assume_unchanged_converted=False)
            def make() -> bool:
                called.append(1)
                return True

            assert creg.create(strcs.NotSpecifiedMeta) is strcs.NotSpecified
            assert called == [1]

        it "turns a dictionary into the object", creator: strcs.Creator, creg: strcs.CreateRegister:
            called = []

            @define
            class Thing:
                one: int
                two: str

            @creator(Thing)
            def make() -> dict:
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
            def make() -> dict:
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
            def make2() -> dict:
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

        it "can use register.create in the creator using the type currently being created", creator: strcs.Creator, creg: strcs.CreateRegister:

            @define
            class Thing:
                one: int
                identity: tp.Annotated[str, strcs.FromMeta("identity")]

            @define
            class Things:
                thing1: Thing

            @creator(Things)
            def create_thing(
                value: object,
                want: strcs.Type,
                /,
                _meta: strcs.Meta,
                _register: strcs.CreateRegister,
            ) -> Things | None:
                if not isinstance(value, int):
                    return None
                return _register.create(
                    want,
                    {"thing1": {"one": value}},
                    meta=_meta.clone({"identity": secrets.token_hex(10)}),
                )

            things = creg.create(Things, 2)
            assert isinstance(things, Things)
            assert isinstance(things.thing1, Thing)
            assert things.thing1.one == 2
            assert len(things.thing1.identity) == 20

            things2 = creg.create(Things, 5)
            assert isinstance(things2, Things)
            assert isinstance(things2.thing1, Thing)
            assert things2.thing1.one == 5
            assert len(things2.thing1.identity) == 20

            assert things.thing1.identity != things2.thing1.identity

        it "can use register.create in the creator using the type currently being created without a layer of indirection", creator: strcs.Creator, creg: strcs.CreateRegister:

            @define
            class Thing:
                one: int
                identity: tp.Annotated[str, strcs.FromMeta("identity")]

            @creator(Thing)
            def create_thing(
                value: object,
                want: strcs.Type,
                /,
                _meta: strcs.Meta,
                _register: strcs.CreateRegister,
            ) -> Thing | None:
                if not isinstance(value, int):
                    return None
                return _register.create(
                    want,
                    {"one": value},
                    meta=_meta.clone({"identity": secrets.token_hex(10)}),
                )

            thing = creg.create(Thing, 2)
            assert isinstance(thing, Thing)
            assert thing.one == 2
            assert len(thing.identity) == 20

            thing2 = creg.create(Thing, 5)
            assert isinstance(thing2, Thing)
            assert thing2.one == 5
            assert len(thing2.identity) == 20

            assert thing.identity != thing2.identity

        describe "generator creator":
            it "can modify the created object inside the creator", creator: strcs.Creator, creg: strcs.CreateRegister:

                @define(slots=False)
                class Thing:
                    one: int

                    def __post_attrs_init__(self):
                        self.two = None

                @creator(Thing)
                def make(value: object) -> tp.Generator[dict | bool, Thing, None]:
                    if not isinstance(value, dict):
                        return None
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
                def make(value: object) -> tp.Generator[dict, Thing, None]:
                    if not isinstance(value, dict):
                        return None
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
                def make(value: object) -> tp.Generator[dict, Thing, None]:
                    if False:
                        yield value

                    return None

                with pytest.raises(strcs.errors.UnableToConvert):
                    creg.create(Thing, {"one": 20})

            it "uses the first yielded thing to determine what is made", creator: strcs.Creator, creg: strcs.CreateRegister:

                @define(slots=False)
                class Thing:
                    one: int = 1

                @creator(Thing)
                def make(
                    value: object,
                ) -> tp.Generator[dict | Thing | type[strcs.NotSpecified], Thing, None]:
                    if not isinstance(value, (dict, Thing, type(strcs.NotSpecified))):
                        return None
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

                def recursion_is_fun(value: object) -> tp.Generator[dict, Thing, None]:
                    assert isinstance(value, dict)
                    assert value == {"one": 20}
                    called.append(2)
                    made = yield {"one": 60}
                    made.two = 500
                    called.append(3)

                @creator(Thing)
                def make(
                    value: object,
                ) -> tp.Generator[tp.Generator[dict, Thing, None], Thing, None]:
                    called.append(1)
                    made = yield recursion_is_fun(value)
                    made.three = 222
                    called.append(4)

                made = creg.create(Thing, {"one": 20})
                assert isinstance(made, Thing)
                assert made.one == 60
                assert made.two == 500
                assert made.three == 222
                assert called == [1, 2, 3, 4]

            it "uses what is yielded the second time", creator: strcs.Creator, creg: strcs.CreateRegister:

                @define(slots=False)
                class Thing:
                    one: int = 1

                @creator(Thing)
                def make(
                    value: object,
                ) -> tp.Generator[dict | Thing | type[strcs.NotSpecified] | None, Thing, None]:
                    made = yield {"one": 0}
                    assert isinstance(made, Thing)
                    assert made.one == 0
                    if isinstance(value, (dict, Thing, type(strcs.NotSpecified))):
                        yield value
                    else:
                        yield None

                made = creg.create(Thing, {"one": 20})
                assert isinstance(made, Thing)
                assert made.one == 20

                made = creg.create(Thing)
                assert isinstance(made, Thing)
                assert made.one == 1

                thing = Thing(one=4)
                made = creg.create(Thing, thing)
                assert made is thing
