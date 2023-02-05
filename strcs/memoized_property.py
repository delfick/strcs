import collections.abc
import typing as tp

PropRet = tp.TypeVar("PropRet")


class memoized_property(tp.Generic[PropRet]):
    name: str

    class Empty:
        pass

    def __init__(self, func: tp.Callable[..., PropRet]):
        self.func = func
        self.__doc__ = func.__doc__

    def __set_name__(self, owner: type, name: str) -> None:
        self.name = name
        if "_memoized_cache" not in owner.__annotations__:
            raise NotImplementedError("The class this is attached to needs a _cache on it")

    def cache(self, instance: object) -> collections.abc.MutableMapping[str, object]:
        cache = getattr(instance, "_memoized_cache", None)
        assert isinstance(cache, collections.abc.MutableMapping)
        return cache

    @tp.overload
    def __get__(self, instance: None, owner: None) -> "memoized_property":
        ...

    @tp.overload
    def __get__(self, instance: object, owner: type[object]) -> PropRet:
        ...

    def __get__(
        self, instance: object | None, owner: type[object] | None = None
    ) -> tp.Union["memoized_property", PropRet]:
        if instance is None:
            return self

        cache = self.cache(instance)

        if self.name not in cache:
            cache[self.name] = self.func(instance)

        return tp.cast(PropRet, cache[self.name])

    def __delete__(self, instance: object) -> None:
        cache = self.cache(instance)
        if self.name in cache:
            del cache[self.name]
