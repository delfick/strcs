import typing as tp
from collections.abc import MutableMapping

PropRet = tp.TypeVar("PropRet")


class memoized_property(tp.Generic[PropRet]):
    """
    A descriptor that memoizes the value it creates. This requires that
    the object the descriptor is on has a ``_memoized_cache`` attribute that is
    a mutable mapping that lets us save the generated values.

    Usage is::

        class MyClass:
            def __init__(self):
                self._memoized_cache = {}

            @memoized_property
            def expensive(self)->int:
                return perform_expensive_operation()


        instance = MyClass()
        assert instance.expensive == 20
        assert instance.expensive == 20 # This time expensive operation is not run

        # It's possible to remove the cached value
        del instance.expensive
        assert instance.expensive == 20 # Expensive operation runs again
    """

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

    def cache(self, instance: object) -> MutableMapping[str, object]:
        cache = getattr(instance, "_memoized_cache", None)
        assert isinstance(cache, MutableMapping)
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
