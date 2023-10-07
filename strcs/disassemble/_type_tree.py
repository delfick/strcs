import itertools
import typing as tp
from collections import OrderedDict
from collections.abc import Iterable, Sequence

import attrs

from ..memoized_property import memoized_property
from ..standard import union_types
from ._base import Field, Type
from ._cache import TypeCache


class HasOrigBases(tp.Protocol):
    """
    Used to figure out the origin classes for an object.
    """

    __orig_bases__: tuple[object]

    @classmethod
    def has(self, thing: object) -> tp.TypeGuard["HasOrigBases"]:
        return isinstance(getattr(thing, "__orig_bases__", None), tuple)

    @classmethod
    def determine_orig_bases(cls, orig: object | None, mro: Sequence[type]) -> Sequence[object]:
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
        if HasOrigBases.has(orig):
            bases = [tp.get_origin(base) or base for base in orig.__orig_bases__]
            if any(mro.index(base) == 1 for base in bases):
                return orig.__orig_bases__

        return list(mro)[1:]


class MRO:
    """
    This class represents the type Hierarchy of an object.

    Using this class it is possible to figure out the hierarchy of the underlying
    classes and the typevars for this object and all objects in it's hierarchy.

    As well as match the class against fields and determine closest type match for
    typevars.

    An instance of this object may be created using the ``create`` classmethod:

    .. code-block:: python

        import my_code
        import strcs


        type_cache = strcs.TypeCache()
        mro = strcs.MRO.create(my_code.my_class, type_cache)

    Or via the ``mro`` property on a :class:`strcs.Type` instance:

    .. code-block:: python

        import my_code
        import strcs


        type_cache = strcs.TypeCache()
        typ = type_cache.disassemble(my_code.my_class)
        mro = typ.mro
    """

    _memoized_cache: dict[str, object]

    @attrs.define
    class Referal:
        """
        An ``attrs`` class used to represent when one type var is defined in
        terms of another.
        """

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

        orig_bases = HasOrigBases.determine_orig_bases(origin, mro)
        bases = [type_cache.disassemble(base) for base in orig_bases]

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

        So for example, getting the typevars for ``Two`` in the following example:

        .. code-block:: python

            import typing as tp
            import strcs

            T = tp.TypeVar("T")
            T = tp.TypeVar("U")


            class One(tp.Generic[T]):
                pass

            class Two(tp.Generic[U], One[U]):
                pass

            type_cache = strcs.TypeCache()
            typevars = type_cache.disassemble(Two).mro.typevars

        Will result in having:

        .. code-block:: python

            {
                (Two, U): strcs.Type.Missing,
                (One, T): MRO.Referal(owner=Two, typevar=U, value=strcs.Type.Missing)
            }

        And for ``Two[str]``:

        .. code-block:: python

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
        """
        Return an ordered tuple of all the type vars that make up this object
        taking into account type vars on this object as well as all inherited
        objects.
        """
        if self.origin in union_types:
            return ()

        result: list[Type | type[Type.Missing]] = []
        typevars = list(self.typevars.items())
        if self.args and not typevars and self.origin not in union_types:
            return tuple(self.type_cache.disassemble(arg) for arg in self.args)

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
                typed = self.type_cache.disassemble(value)
            else:
                typed = Type.Missing

            result.insert(0, typed)

        return tuple(result)

    @memoized_property
    def signature_for_display(self) -> str:
        """
        Return a string representing the filled types for this object.

        For example:

        .. code-block:: python

            import typing as tp
            import strcs

            T = tp.TypeVar("T")
            U = tp.TypeVar("U")


            class One(tp.Generic[T]):
                pass


            class Two(tp.Generic[U], One[U]):
                pass


            type_cache = strcs.TypeCache()
            typ1 = type_cache.disassemble(One)
            typ2 = type_cache.disassemble(One[int])
            typ3 = type_cache.disassemble(Two[str])

            assert typ1.mro.signature_for_display == "~T"
            assert typ2.mro.signature_for_display == "int"
            assert typ3.mro.signature_for_display == "str"

        It is used by :class:`strcs.Type` in it's ``for_display`` method to give a
        string representation of the object it is wrapping.
        """
        found_with_missing: set[type] = set()
        signature_typevars: list[tuple[tp.TypeVar | int, object]] = []
        for (owner, tv), value in self.typevars.items():
            if value is Type.Missing and owner in self.bases:
                found_with_missing.add(owner)
                if len(found_with_missing) > 1:
                    continue
                signature_typevars.append((tv, value))
            elif owner is self.origin and not isinstance(value, self.Referal):
                signature_typevars.append((tv, value))

        if not signature_typevars:
            return ""

        result: list[str] = []
        for tv, value in signature_typevars:
            if value is Type.Missing:
                result.append(repr(tv))
            else:
                result.append(self.type_cache.disassemble(value).for_display())

        return ", ".join(result)

    @memoized_property
    def raw_fields(self) -> tp.Sequence[Field]:
        """
        Return a sequence of :class:`strcs.Field` objects representing all the
        annotated fields on the class, including those it receives from it's
        ancestors.

        These field objects will not contain converted types (any type variables
        are not resolved).

        The ``fields`` method on the ``MRO`` object will take these fields
        and resolve the type vars.
        """
        result: list[Field] = []
        for cls in reversed(self.mro):
            disassembled = self.type_cache.disassemble.typed(object, cls)
            fields = disassembled.raw_fields

            for field in fields:
                found: bool = False
                for f in result:
                    if f.name == field.name:
                        if f.type != field.type:
                            f.original_owner = cls

                        f.default = field.default
                        f.kind = field.kind
                        f.disassembled_type = self.type_cache.disassemble(field.type)
                        f.owner = cls
                        found = True
                        break
                if not found:
                    result.append(field.clone())

        return result

    @memoized_property
    def fields(self) -> tp.Sequence[Field]:
        """
        Return a sequence of :class:`strcs.Field` objects representing the fields
        on the object, after resolving the type vars.

        Type vars are resolved by understanding how type variables are filled out
        on the outer object, and how that relates to type variables being used
        to make up other type variables.
        """
        typevars = self.typevars
        fields: list[Field] = []

        for field in self.raw_fields:
            field_type = field.type
            field_type_info = self.type_cache.disassemble(field_type)

            extracted = field_type_info.extracted
            if isinstance(extracted, tp.TypeVar):
                field_type = extracted

            if isinstance(field_type, tp.TypeVar):
                replacement = typevars[
                    (self.type_cache.disassemble(field.original_owner).checkable, field_type)
                ]
                if isinstance(replacement, self.Referal):
                    replacement = replacement.value
                if replacement is not Type.Missing:
                    field_type = replacement
                else:
                    field_type = object

            field_type = field_type_info.reassemble(field_type)
            fields.append(field.with_replaced_type(self.type_cache.disassemble(field_type)))

        return fields

    def find_subtypes(self, *want: type) -> Sequence["Type"]:
        """
        This method will take in a tuple of expected types and return a matching
        list of types from the type variables on the object.

        The wanted types must be parents of the filled type variables and in the
        correct order for the function to not raise an error.

        For example:

        .. code-block:: python

            import typing as tp
            import strcs

            T = tp.TypeVar("T")


            class A:
                pass


            class B(A):
                pass


            class C(A):
                pass


            class One(tp.Generic[T]):
                pass


            type_cache = strcs.TypeCache()
            typ1 = type_cache.disassemble(One[B])
            typ2 = type_cache.disassemble(One[C])

            assert typ1.mro.find_subtypes(A) == (B, )
            assert typ2.mro.find_subtypes(A) == (C, )
        """
        typevars = self.typevars
        result: list["Type"] = []

        for tvrs, wa in itertools.zip_longest(self.typevars, want):
            if tvrs is None:
                owner, tv = None, None
            else:
                owner, tv = tvrs

            if wa is None:
                break
            if tv is None or owner is None:
                raise ValueError(
                    f"The type has less typevars ({len(self.typevars)}) than wanted ({len(want)})"
                )

            typ = self.type_cache.disassemble(typevars[(owner, tv)])

            if not issubclass(
                typ.checkable,
                self.type_cache.disassemble(wa).checkable,
            ):
                raise ValueError(
                    f"The concrete type {typ} is not a subclass of what was asked for {wa}"
                )

            result.append(typ)

        return tuple(result)
