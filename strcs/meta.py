from collections.abc import Mapping
import typing as tp
import fnmatch

T = tp.TypeVar("T")
U = tp.TypeVar("U")


class Empty:
    pass


class NarrowCB(tp.Protocol):
    def __call__(self, *patterns: str, obj: Mapping | object = Empty) -> dict[str, tp.Any]:
        ...


class Narrower:
    """
    Used to take some dictionary and return a constrained version of it

    Usage::

        narrower = Narrower(obj)
        narrowed = narrower.narrow("key1", "key2")

    Where the narrow options are fnmatch globs for top level keys in the obj
    and the obj is either a Mapping (dictionary like) or any other kind of object.
    """

    class Progress:
        def __init__(self, obj: Mapping | object):
            self.obj = obj

            self.collected: dict[str, tp.Any] = {}
            self.obj_is_mapping = isinstance(self.obj, Mapping)

        def collect(self, narrow: NarrowCB) -> dict[str, bool]:
            return self.collected

        def add(self, pattern: str, n: str, v: tp.Any):
            if n in self.collected:
                return

            patt = pattern

            if fnmatch.fnmatch(n, patt):
                self.collected[n] = v

    def __init__(self, obj: Mapping | object):
        self.obj = obj

    def keys_from(self, options: tp.Any) -> tp.Iterable[str]:
        if isinstance(options, (Mapping, tp.Iterable)):
            yield from iter(options)
        else:
            yield from [n for n in dir(options) if not n.startswith("_")]

    def narrow(self, *patterns: str, obj: Mapping | object = Empty) -> dict[str, tp.Any]:
        if not patterns:
            return {}

        if obj is Empty:
            obj = self.obj
        progress = self.Progress(obj)

        for pattern in patterns:
            if pattern.startswith("."):
                pattern = pattern[1:]
            for n in self.keys_from(obj):
                if progress.obj_is_mapping:
                    v = tp.cast(Mapping, obj)[n]
                else:
                    v = getattr(obj, n)

                progress.add(pattern, n, v)

        return progress.collect(self.narrow)


def extract_type(typ: T) -> tp.Tuple[bool, U]:
    """
    Given some type, return a tuple of (optional, type)

    So str would return (False, str)

    whereas tp.Optional[str] would return (True, str)

    and str | bool would return (False, str | bool)

    but tp.Optional[str | bool] would return (True, str | bool)
    """
    optional = False
    if tp.get_origin(typ) is tp.Union:
        args = tp.get_args(typ)
        if len(args) > 1 and isinstance(args[-1], type) and issubclass(args[-1], type(None)):
            if len(args) == 2:
                typ = args[0]
            else:
                # A tp.Optional[tp.Union[arg1, arg2]] is equivalent to tp.Union[arg1, arg2, None]
                # So we must create a copy of the union with just arg1 | arg2
                # We tell mypy to be quiet with the noqa because I can't make it understand typ is a Union
                typ = typ.copy_with(args[:-1])  # type: ignore
            optional = True

    return optional, tp.cast(U, typ)
