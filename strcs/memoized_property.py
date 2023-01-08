import typing as tp

T = tp.TypeVar("T")


class memoized_property(tp.Generic[T]):
    class Empty:
        pass

    def __init__(self, func: tp.Callable[..., T]):
        self.func = func
        self.name = func.__name__
        self.__doc__ = func.__doc__
        self.cache_name = "_{0}".format(self.name)

    def __get__(self, instance: object = None, owner: object = None) -> T:
        if instance is None:
            return tp.cast(T, self)

        if getattr(instance, self.cache_name, self.Empty) is self.Empty:
            setattr(instance, self.cache_name, self.func(instance))
        return getattr(instance, self.cache_name)

    def __set__(self, instance, value):
        setattr(instance, self.cache_name, value)

    def __delete__(self, instance):
        if hasattr(instance, self.cache_name):
            delattr(instance, self.cache_name)
