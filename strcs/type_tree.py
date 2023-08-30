import dataclasses
import itertools
import typing as tp
from collections import OrderedDict
from collections.abc import Iterable, Sequence

from .disassemble import Type, TypeCache, union_types
from .memoized_property import memoized_property


class HasOrigBases(tp.Protocol):
    __orig_bases__: tuple[object]

    @classmethod
    def match(self, thing: object) -> tp.TypeGuard["HasOrigBases"]:
        return isinstance(getattr(thing, "__orig_bases__", None), tuple)


class MRO:
    """
    This class represents the type Hierarchy of an object.

    Using this class it is possible to figure out the MRO of the underlying classes and
    the typevars for this object and all objects in it's hierarchy.

    As well as match the class against fields and determine closest type match for
    typevars.
    """

    _memoized_cache: dict[str, object]

    @dataclasses.dataclass
    class Referal:
        owner: type
        typevar: tp.TypeVar
        value: object

    @classmethod
    def create(cls, start: object | None, type_cache: TypeCache) -> "MRO":
        """
        Given some object and a type cache, return a filled instance of the MRO.
        """
        args = tp.get_args(start) or ()

        mro: tuple[type, ...]
        origin: type | None

        origin = start if isinstance(start, type) and not args else tp.get_origin(start)
        mro = () if origin is None or not hasattr(origin, "__mro__") else origin.__mro__

        def determine_orig_bases(orig: object | None) -> Sequence[object]:
            """
            Determine the classes to use for our bases.

            Python type annotations are difficult to parse and does not make our lives easy here.

            ``tp.get_origin`` and ``__orig_bases__`` are specific to generics and we want to know
            if this class is not generic, has generic as a direct parent, or generic as a distant
            parent.

            The ``__orig_bases__`` will itself contain filled generics this class is based off and so
            we get the unsubscripted class of those and look for them in the mro.

            If any of them are the second in the list, then that means they have come directly from this
            class and not from a distant parent.
            """
            if HasOrigBases.match(orig):
                bases = [tp.get_origin(base) or base for base in orig.__orig_bases__]
                if any(mro.index(base) == 1 for base in bases):
                    return orig.__orig_bases__

            return list(mro)[1:]

        orig_bases = determine_orig_bases(origin)
        bases = [Type.create(base, expect=object, cache=type_cache) for base in orig_bases]

        return cls(
            _start=start, _origin=origin, _args=args, _mro=mro, _bases=bases, _type_cache=type_cache
        )

    def __init__(
        self,
        *,
        _start: object | None,
        _args: tuple[object, ...],
        _origin: type | None,
        _mro: None | tuple[type, ...],
        _bases: Sequence[Type],
        _type_cache: TypeCache,
    ):
        self.start = _start
        self.args = _args
        self.origin = _origin
        self.mro = () if _mro is None else _mro
        self.bases = _bases
        self.type_cache = _type_cache
        self._memoized_cache = {}

    @memoized_property
    def typevars(self) -> OrderedDict[tuple[type, tp.TypeVar | int], object]:
        """
        Return an ordered dictionary mapping all the typevars in this objects MRO with their value.

        The keys to the dictionary are a tuple of (class, typevar).

        So for example, getting the typevars for ``Two`` in the following example::

            import typing as tp
            import strcs

            T = tp.TypeVar("T")
            T = tp.TypeVar("U")



            class One(tp.Generic[T]):
                pass

            class Two(tp.Generic[U], One[U]):
                pass

        Will result in having::

            {
                (Two, U): strcs.Type.Missing,
                (One, T): MRO.Referal(owner=Two, typevar=U, value=strcs.Type.Missing)
            }

        And for ``Two[str]``::

            {
                (Two, U): str,
                (One, T): MRO.Referal(owner=Two, typevar=U, value=str)
            }
        """
        values: OrderedDict[tuple[type, tp.TypeVar | int], object] = OrderedDict()

        parameters: list[tp.TypeVar | tp.ParamSpec] = []
        if (
            (origin := self.origin)
            and hasattr(origin, "__parameters__")
            and isinstance(origin.__parameters__, Iterable)
        ):
            for param in origin.__parameters__:
                assert isinstance(param, (tp.TypeVar, tp.ParamSpec))
                parameters.append(param)

        for index, (tv, val) in enumerate(itertools.zip_longest(parameters, self.args)):
            assert tv is not Type.Missing, tv
            assert (origin := self.origin) is not None, origin

            if not isinstance(tv, tp.TypeVar):
                if origin is tp.Generic:
                    continue
                values[(origin, index + 1)] = val
            else:
                values[(origin, tv)] = Type.Missing if val is None else val

        for base in self.bases:
            for (origin, tv), val in base.mro.typevars.items():
                if (origin, tv) in values:
                    continue

                if isinstance(val, tp.TypeVar):
                    assert val in parameters

                    orig = self.origin
                    assert orig is not None

                    value = values[(orig, val)]
                    if isinstance(value, tp.TypeVar):
                        val = MRO.Referal(owner=orig, typevar=val, value=Type.Missing)
                    else:
                        val = MRO.Referal(owner=orig, typevar=val, value=value)

                values[(origin, tv)] = val

        for (origin, tv), val in list(values.items()):
            value = val
            while isinstance(value, MRO.Referal):
                value = values.get((value.owner, value.typevar), Type.Missing)

            if isinstance(val, MRO.Referal):
                val.value = value

        return values

    @memoized_property
    def all_vars(self) -> tuple[Type | type[Type.Missing], ...]:
        if self.origin in union_types:
            return ()

        result: list[Type | type[Type.Missing]] = []
        typevars = list(self.typevars.items())
        if self.args and not typevars and self.origin not in union_types:
            return tuple(Type.create(arg, cache=self.type_cache) for arg in self.args)

        found: set[tuple[type, tp.TypeVar | int]] = set()

        for key, value in reversed(typevars):
            if isinstance(value, self.Referal):
                key = (value.owner, value.typevar)
                value = value.value

            if key in found:
                continue

            found.add(key)

            typed: Type | type[Type.Missing]
            if value is not Type.Missing:
                typed = Type.create(value, cache=self.type_cache)
            else:
                typed = Type.Missing

            result.insert(0, typed)

        return tuple(result)
