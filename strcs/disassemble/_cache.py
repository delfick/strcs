import typing as tp
from collections.abc import MutableMapping

from ._comparer import Comparer

if tp.TYPE_CHECKING:
    from ._base import Disassembler, Type

U = tp.TypeVar("U")


class _TypeCacheDisassembler:
    def __init__(self, type_cache: "TypeCache"):
        from ._base import Type

        self.Type = Type
        self.type_cache = type_cache

    @tp.overload
    def __call__(self, typ: type[U]) -> "Type[U]":
        ...

    @tp.overload
    def __call__(self, typ: "Type[U]") -> "Type[U]":
        ...

    @tp.overload
    def __call__(self, typ: object) -> "Type[object]":
        ...

    def __call__(self, typ: type[U] | object) -> "Type[U] | Type[object]":
        """
        Return a new :class:`strcs.Type` for the provided object using this
        type cache
        """
        return self.Type.create(typ, expect=object, cache=self.type_cache)

    def typed(self, expect: type[U], typ: object) -> "Type[U]":
        """
        Return a new :class:`strcs.Type` for the provided object using this
        type cache and the expected type.
        """
        return self.Type.create(typ, expect=expect, cache=self.type_cache)


class TypeCache(MutableMapping[object, "Type"]):
    """
    The ``TypeCache`` is used to memoize the :class:`strcs.Type` objects that get created
    because the creation of :class:`strcs.Type` objects is very deterministic.

    It can be treated like a mutable mapping:

    .. code-block:: python

        # Note though that most usage should be about passing around a type cache
        # and not needing to interact with it directly.

        type_cache = strcs.TypeCache()

        typ = type_cache.disassemble(int)

        assert type_cache[int] is typ
        assert int in type_cache
        assert list(type_cache) == [(type, int)]

        # Can delete individual types
        del type_cache[int]

        assert int not in type_cache

        # Can clear all types
        type_cache.clear()
    """

    disassemble: "Disassembler"
    """Used to create new Types using this type cache"""

    def __init__(self) -> None:
        self.cache: dict[tuple[type, object], "Type"] = {}
        self.disassemble = _TypeCacheDisassembler(self)
        self.comparer = Comparer(self)

    def key(self, o: object) -> tuple[type, object]:
        return (type(o), o)

    def __getitem__(self, k: object) -> "Type":
        return self.cache[self.key(k)]

    def __setitem__(self, k: object, v: "Type") -> None:
        try:
            hash(k)
        except TypeError:
            return
        else:
            self.cache[self.key(k)] = v

    def __delitem__(self, k: object) -> None:
        del self.cache[self.key(k)]

    def __contains__(self, k: object) -> bool:
        try:
            hash(k)
        except TypeError:
            return False
        else:
            return self.key(k) in self.cache

    def __iter__(self) -> tp.Iterator[object]:
        return iter(self.cache)

    def __len__(self) -> int:
        return len(self.cache)

    def clear(self) -> None:
        self.cache.clear()
