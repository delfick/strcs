"""
The ``creator`` decorator is used to register a callable that will be used to
transform provided objects into their desired types.

For example:

.. code-block:: python

    import strcs
    import attrs

    reg = strcs.CreateRegister()
    creator = reg.make_decorator()


    @attrs.define
    class Thing:
        one: int


    @creator(Thing)
    def create_thing(value: object, /) -> strcs.ConvertResponse[Thing]:
        # receives the {"one": 20} provided below
        ...


    thing = reg.create(Thing, {"one": 20})

There are a range of signatures that these creator functions may take so that
``strcs`` only needs to provide information that is requested. Also, ``strcs``
will ensure the correct creators are used as types are encountered during the
course of creating some value and all the nested attributes it contains.

In ``strcs`` parlance, the function that developers interact with are
``strcs.ConvertDefinition[T]`` and the normalised form that ``strcs`` works with
is ``strcs.ConvertFunction[T]``.

``strcs.ConvertDefinition[T]`` functions return objects matching ``strcs.ConvertResponse[T]``:

    * None - the provided value couldn't be turned into our desired object
    * An instance of T - use as is without further transformation
    * True - use the provided value. Complain if that value is ``strcs.NotSpecified``
    * A mutable map - If the provided type is a class, then cattrs logic will be
      used to turn that map into an instance of the desired class.
    * A generator function - See below

If a ``ConvertDefinition`` is a generator, then the developer has an opportunity
to make changes to the object after ``strcs`` has created the object:

.. code-block:: python

    @creator(Thing)
    def create_thing(value: object, /) -> strcs.ConvertResponse[Thing]:
        if not isinstance(value, int):
            return None

        res = yield {"one": value}
        assert isinstance(res, Thing)
        assert res.one == value

        res.do_something()
        # We don't yield again, so res is the value that is used

Note that if the generator only yields once, then that result is the one that
is used. If the generator yields a second time, then that value will be passed
through ``strcs`` logic just as the first yield was.

The ``WrappedCreator`` object is used to take ``ConvertDefinition`` functions
and provide a ``ConvertFunction`` interface for executing them and is used
by the function returned by ``strcs.CreateRegister::make_decorator``
"""
import inspect
import typing as tp
from collections.abc import Mapping

import attrs
import cattrs

from . import errors
from .args_extractor import ArgsExtractor
from .disassemble import Type, TypeCache, instantiate
from .meta import Meta
from .not_specified import NotSpecified, NotSpecifiedMeta
from .standard import builtin_types

if tp.TYPE_CHECKING:
    from .register import CreateRegister

T = tp.TypeVar("T")


@attrs.define
class CreateArgs(tp.Generic[T]):
    """
    The object given to ``ConvertFunction`` objects to produce an instance of the
    desired type.
    """

    value: object
    want: Type[T]
    meta: Meta
    converter: cattrs.Converter
    register: "CreateRegister"


# ConvertResponse represents what a creator can return
# Either a value instructing strcs to do something, an object that strcs should
# use as is, or a generator that can operate on the object strcs creates.
ConvertResponseValues: tp.TypeAlias = bool | dict[str, object] | T | NotSpecifiedMeta
ConvertResponseGenerator: tp.TypeAlias = tp.Generator[
    tp.Optional[ConvertResponseValues[T] | tp.Generator], T, None
]
ConvertResponse: tp.TypeAlias = tp.Optional[ConvertResponseValues[T] | ConvertResponseGenerator[T]]

# ConvertDefinition is the developer provided functions that do transformation
# They may be of the form
# - ()
# - (value, /)
# - (value, /, meta1, meta2, ...)
# - (value, want, /)
# - (value, want, /, meta1, meta2, ...))
# - (meta1, meta2, ...)
# Where
# - value: object = The value being transformed
# - want: Type[T] = The strcs.Type object for the desired type
# - meta values are from the meta object, or the special objects known by
#   strcs.ArgExtractor
ConvertDefinition: tp.TypeAlias = tp.Callable[..., ConvertResponse[T]]

# ConvertFunction is the object the strcs.CreateRegister interacts with to invoke
# the ConvertDefinition objects.
ConvertFunction: tp.TypeAlias = tp.Callable[[CreateArgs[T]], T]


def take_or_make(value: object, want: Type[T], /) -> ConvertResponse[T]:
    """
    A ConvertDefinition that is used when one isn't found in the registry.

    It will either return the value as is if it can be considered to already be
    what we want or if we can use it to make such an object.

    Otherwise it returns None so that strcs can complain.
    """
    if want.is_type_for(value):
        return value
    elif isinstance(value, (dict, NotSpecifiedMeta)):
        return value
    else:
        return None


class WrappedCreator(tp.Generic[T]):
    """
    An implementation of ``strcs.ConvertFunction`` that operates on the provided
    ConvertDefinition.
    """

    func: ConvertDefinition[T]

    def __init__(
        self,
        typ: Type[T],
        func: ConvertDefinition[T] | None = None,
        *,
        type_cache: TypeCache,
        assume_unchanged_converted: bool = True,
    ):
        self.typ = typ
        self.type_cache = type_cache
        self.assume_unchanged_converted = assume_unchanged_converted

        if func is None:
            self.func = take_or_make
        else:
            self.func = func

        if hasattr(func, "side_effect"):
            # Hack to deal with mock objects
            side_effect = getattr(func, "side_effect")
            assert callable(side_effect)
            self.signature = inspect.signature(side_effect)
        else:
            assert callable(self.func)
            self.signature = inspect.signature(self.func)

    def __eq__(self, o: object) -> bool:
        return o == self.func or (isinstance(o, WrappedCreator) and o.func == self.func)

    def __repr__(self):
        return f"<Wrapped {self.func}>"

    def __call__(self, create_args: "CreateArgs") -> T:
        want = create_args.want
        meta = create_args.meta
        value = create_args.value
        register = create_args.register
        converter = create_args.converter

        if self.assume_unchanged_converted and want.is_type_for(value):
            if want.origin_type not in builtin_types:
                return tp.cast(T, value)

        try:
            args = ArgsExtractor(
                signature=self.signature,
                value=value,
                want=want,
                meta=meta,
                converter=converter,
                register=register,
                creator=self.func,
            ).extract()
        except Exception as error:
            raise errors.UnableToConvert(
                converting=value,
                into=want,
                reason="Failed to determine arguments for creator",
                error=error,
                creator=self.func,
            )

        try:
            res = self.func(*args)
        except Exception as error:
            raise errors.UnableToConvert(
                converting=value,
                into=want,
                reason="Failed to invoke creator",
                error=error,
                creator=self.func,
            )

        def deal(res: ConvertResponse[T], value: object) -> T:
            if inspect.isgenerator(res):
                try:
                    return self._process_generator(res, value, deal)
                except errors.UnableToConvert:
                    raise
                except Exception as error:
                    raise errors.UnableToConvert(
                        converting=value,
                        into=want,
                        reason="Something went wrong in the creator generator",
                        error=error,
                        creator=self.func,
                    )
            elif res is None:
                raise errors.UnableToConvert(
                    converting=type(value),
                    into=want,
                    reason="Converter didn't return a value to use",
                    creator=self.func,
                )
            elif want.is_equivalent_type_for(res):
                return res
            elif res is True:
                if value is NotSpecified and not want.checkable == type(NotSpecified):
                    raise errors.UnableToConvert(
                        converting=value,
                        into=want,
                        reason="Told to use NotSpecified as the final value",
                        creator=self.func,
                    )
                return tp.cast(T, value)
            else:
                if not isinstance(res, Mapping) and issubclass(
                    want.checkable, self.type_cache.disassemble(type(res)).checkable
                ):
                    raise errors.SupertypeNotValid(
                        want=want.checkable,
                        got=self.type_cache.disassemble(type(res)).checkable,
                        reason="A Super type is not a valid value to convert",
                    )

                try:
                    return instantiate(want, res, converter)
                except Exception as error:
                    raise errors.UnableToConvert(
                        converting=value,
                        into=want,
                        reason="Failed to create",
                        error=error,
                        creator=self.func,
                    )

        return deal(res, value)

    def _process_generator(
        self,
        res: ConvertResponseGenerator[T],
        value: object,
        deal: tp.Callable[[ConvertResponse[T], object], T],
    ) -> T:
        try:
            made: ConvertResponse[T]

            try:
                made = deal(next(res), value)
            except StopIteration:
                made = None
            else:
                try:
                    made2 = res.send(made)
                    if made2 is True:
                        value = made
                    made = made2
                except StopIteration:
                    pass

            return deal(made, value)
        finally:
            res.close()
