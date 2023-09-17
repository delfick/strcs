import typing as tp
from collections.abc import MutableMapping

if tp.TYPE_CHECKING:
    from ._base import Type


class TypeCache(MutableMapping[object, "Type"]):
    """
    The ``TypeCache`` is used to memoize the :class:`strcs.Type` objects that get created
    because the creation of :class:`strcs.Type` objects is very deterministic.

    It can be treated like a mutable mapping:

    .. code-block:: python

        # Note though that most usage should be about passing around a type cache
        # and not needing to interact with it directly.

        type_cache = strcs.TypeCache()

        typ = strcs.Type.create(int, cache=type_cache)

        assert type_cache[int] is typ
        assert int in type_cache
        assert list(type_cache) == [(type, int)]

        # Can delete individual types
        del type_cache[int]

        assert int not in type_cache

        # Can clear all types
        type_cache.clear()
    """

    def __init__(self):
        self.cache = {}

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
