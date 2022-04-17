from collections.abc import Mapping
from attrs import define
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

    If a pattern has a dot in it, then it will be used to match against nested objects
    with preference given to keys that match with the dot.

    So::

        obj = {"a": {"b": {"d": 4, "e": 5}}, "a.b": 1, "a.c": 3}
        assert Narrower(obj).narrow("a.b") == {"a.b": 1}
        assert Narrower(obj).narrow("a.c") == {"a.c": 3}
        assert Narrower(obj).narrow("a.b.d") == {"a.b.d": 4}
        assert Narrower(obj).narrow("a.b.*") == {"a.b.d": 4, "a.b.e": 5}
        assert Narrower(obj).narrow("a.b*") == {"a.b.d": 4, "a.b.e": 5}

        obj = {"a": {"b": {"d": 4, "e": 5}}, "a.b": {"f": 6}, "a.bc": True}
        assert Narrower(obj).narrow("a.b") == {"a.b": {"f": 6}}
        assert Narrower(obj).narrow("a.b.d") == {"a.b.d": 4}
        assert Narrower(obj).narrow("a.b.*") == {"a.b.d": 4, "a.b.e": 5, "a.b.f": 6}
        assert Narrower(obj).narrow("a.b*") == {"a.b": {"f": 6}, "a.bc": True}
    """

    @define
    class Further:
        value: tp.Any
        patterns: list[str]

    class Progress:
        def __init__(self, obj: Mapping | object):
            self.obj = obj

            self.further: dict[str, Narrower.Further] = {}
            self.collected: dict[str, tp.Any] = {}
            self.obj_is_mapping = isinstance(self.obj, Mapping)

        def collect(self, narrow: NarrowCB) -> dict[str, bool]:
            for n, ft in self.further.items():
                found = narrow(*ft.patterns, obj=ft.value)
                for k, v in found.items():
                    key = f"{n}.{k}"
                    if key not in self.collected:
                        self.collected[key] = v

            return self.collected

        def add(self, pattern: str, n: str, v: tp.Any):
            if n in self.collected:
                return

            patt = pattern
            if pattern.startswith("*"):
                patt = f"{n}{pattern[1:]}"

            is_nestable = not (
                not isinstance(v, (Mapping, type))
                and v.__class__.__module__ in ("__builtin__", "builtins")
            )

            if patt.startswith(f"{n}.") and is_nestable:
                if n not in self.further:
                    self.further[n] = Narrower.Further(value=v, patterns=[])
                self.further[n].patterns.append(patt[len(f"{n}.") :])
            elif fnmatch.fnmatch(n, patt):
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
