import collections
import typing as tp

if tp.TYPE_CHECKING:
    from .base import Type


class TypeCache(collections.abc.MutableMapping[object, "Type"]):
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
