from .meta import Meta
from . import errors

from attrs import define
import typing as tp
import inspect
import cattrs
import attrs

T = tp.TypeVar("T")


class NotSpecifiedMeta(type):
    def __repr__(self):
        return "<NotSpecified>"


class NotSpecified(metaclass=NotSpecifiedMeta):
    def __init__(self):
        raise Exception("Do not instantiate NotSpecified")


ConvertResponseValues: tp.TypeAlias = tp.Optional[bool | dict[str, tp.Any]]
ConvertResponseDirect: tp.TypeAlias = tp.Union[
    ConvertResponseValues, tp.Tuple[ConvertResponseValues, Meta]
]
ConvertResponseGenerator: tp.TypeAlias = tp.Generator[ConvertResponseValues | T, T, None]

ConvertResponse: tp.TypeAlias = ConvertResponseDirect | ConvertResponseGenerator[T] | T

ConvertDefinitionValue: tp.TypeAlias = tp.Callable[[tp.Any], ConvertResponse[T]]
ConvertDefinitionNoValue: tp.TypeAlias = tp.Callable[[], ConvertResponse[T]]
ConvertDefinitionValueAndType: tp.TypeAlias = tp.Callable[[tp.Any, tp.Type], ConvertResponse[T]]


class ConvertDefinitionValueAndData(tp.Protocol):
    def __call__(self, value: tp.Any, /, *values: tp.Any) -> ConvertResponse[T]:
        ...


class ConvertDefinitionValueAndTypeAndData(tp.Protocol):
    def __call__(self, value: tp.Any, want: tp.Type, /, *values: tp.Any) -> ConvertResponse[T]:
        ...


ConvertDefinition: tp.TypeAlias = tp.Union[
    ConvertDefinitionValue[T],
    ConvertDefinitionNoValue[T],
    ConvertDefinitionValueAndType[T],
    ConvertDefinitionValueAndData,
    ConvertDefinitionValueAndTypeAndData,
]
ConvertFunction: tp.TypeAlias = tp.Callable[[tp.Any, tp.Type, Meta, cattrs.Converter], T]


def take_or_make(value: tp.Any, typ: tp.Type[T], /) -> ConvertResponse:
    if isinstance(value, typ):
        return value
    elif value is NotSpecified or isinstance(value, dict):
        return value
    else:
        return None


def fromdict(converter: cattrs.Converter, register: "CreateRegister", res: tp.Any, want: T) -> T:
    if res is NotSpecified:
        res = {}
    if isinstance(res, dict):
        for field in attrs.fields(want):
            if field.type is not None and field.type in register and field.name not in res:
                res[field.name] = NotSpecified
    return converter.structure_attrs_fromdict(tp.cast(dict, res), want)


@define
class Annotation:
    def adjusted_meta(self, meta: Meta) -> Meta:
        return meta.clone(data_extra={"__call_defined_annotation__": self})


@define
class MergedAnnotation:
    def adjusted_meta(self, meta: Meta) -> Meta:
        clone = meta.clone()
        for field in attrs.fields(self.__class__):
            clone[field.name] = getattr(self, field.name)
        return clone


class CreateRegister:
    def __init__(self):
        self.register: dict[tp.Type[T], ConvertFunction[T]] = {}

    def __setitem__(self, typ: tp.Type[T], creator: ConvertFunction[T]) -> None:
        if not isinstance(typ, type):
            raise errors.CanOnlyRegisterTypes(got=typ)
        self.register[typ] = creator

    def __contains__(self, typ: tp.Type[T]) -> bool:
        return self.creator_for(typ) is not None

    def creator_for(self, typ: tp.Type[T]) -> tp.Optional[ConvertFunction[T]]:
        if hasattr(typ, "__origin__"):
            typ = typ.__origin__

        if not isinstance(typ, type):
            return None

        if typ in self.register:
            return self.register[typ]

        for t, func in self.register.items():
            if issubclass(typ, t):
                return func

        return None

    def create(self, typ: tp.Type[T], value: tp.Any = NotSpecified, meta: tp.Any = NotSpecified):
        if meta is NotSpecified:
            meta = Meta()

        converter = cattrs.Converter()

        cache: dict[tp.Type[T], ConvertFunction[T]] = {}

        def convert(value: tp.Any, want: tp.Type[T]) -> T:
            if hasattr(want, "__origin__") and want.__origin__ is not list:
                ann = want.__metadata__[0]
                m = ann.adjusted_meta(meta)
                want = want.__origin__
                return self.create(want, value, meta=m)

            if want in cache:
                return cache[want](value, want, meta, converter)
            elif isinstance(value, want):
                return value
            else:
                return fromdict(converter, self, value, want)

        def check_func(want: tp.Type[T]) -> bool:
            if hasattr(want, "__origin__") and want.__origin__ is not list:
                want = want.__origin__

                if (
                    hasattr(want, "__origin__")
                    and want.__origin__ is list
                    and len(want.__args__) == 1
                ):
                    want = want.__args__[0]

            creator = self.creator_for(want)
            if creator is not None:
                cache[want] = creator
                return True
            return hasattr(want, "__attrs_attrs__")

        converter.register_structure_hook_func(check_func, convert)
        return converter.structure(value, typ)


class _ArgsExtractor:
    def __init__(
        self,
        signature: inspect.Signature,
        value: tp.Any,
        want: tp.Type,
        meta: Meta,
        converter: cattrs.Converter,
    ):
        self.meta = meta
        self.want = want
        self.value = value
        self.converter = converter
        self.signature = signature

    def extract(self) -> list[tp.Any]:
        use = []
        values = list(self.signature.parameters.values())

        if values and values[0].kind is inspect.Parameter.POSITIONAL_ONLY:
            values.pop(0)
            use.append(self.value)

        if values and values[0].kind is inspect.Parameter.POSITIONAL_ONLY:
            values.pop(0)
            use.append(self.want)

        for param in values:
            if (
                param.annotation is Meta
                or param.annotation is inspect._empty
                and param.name == "meta"
            ):
                use.append(self.meta)
            elif (
                param.annotation is not tp.Any
                and isinstance(param.annotation, type)
                and issubclass(param.annotation, cattrs.Converter)
            ) or (param.annotation is inspect._empty and param.name == "converter"):
                use.append(self.converter)
            elif param.annotation in (inspect._empty, tp.Any):
                use.append(self.meta.retrieve_one(object, param.name))
            else:
                use.append(self.meta.retrieve_one(param.annotation, param.name))

        return use


class CreatorDecorator(tp.Generic[T]):
    func: ConvertDefinition[T]

    def __init__(self, register: CreateRegister, typ: tp.Type[T], assume_unchanged_converted=True):
        self.typ = typ
        self.register = register
        self.assume_unchanged_converted = assume_unchanged_converted

    def __call__(self, func: tp.Optional[ConvertDefinition[T]] = None) -> ConvertDefinition[T]:
        if func is None:
            self.func = take_or_make
        else:
            self.func = func

        if hasattr(self.func, "side_effect"):
            # Hack to deal with mock objects
            self.signature = inspect.signature(self.func.side_effect)  # type: ignore
        else:
            self.signature = inspect.signature(self.func)

        self.register[self.typ] = self.wrapped
        return self.func

    def wrapped(self, value: tp.Any, want: tp.Type, meta: Meta, converter: cattrs.Converter) -> T:
        if self.assume_unchanged_converted and isinstance(value, want):
            return value

        res = self._invoke_func(value, want, meta, converter)

        def deal(res: ConvertResponse[T], value: tp.Any) -> T:
            if inspect.isgenerator(res):
                return self._process_generator(res, value, deal)
            elif res is None:
                raise errors.UnableToConvert(
                    converting=type(value),
                    into=want,
                    reason="Converter didn't return a value to use",
                )
            elif isinstance(res, want) or issubclass(type(res), self.typ):
                return tp.cast(T, res)
            elif res is True:
                if value is NotSpecified and not issubclass(want, type(NotSpecified)):
                    raise errors.UnableToConvert(
                        converting=value,
                        into=want,
                        reason="Told to use NotSpecified as the final value",
                    )
                return tp.cast(T, value)
            else:
                return fromdict(converter, self.register, res, want)

        return deal(res, value)

    def _process_generator(
        self,
        res: ConvertResponseGenerator[T],
        value: tp.Any,
        deal: tp.Callable[[ConvertResponse[T], tp.Any], T],
    ) -> T:
        try:
            made: ConvertResponse[T]

            try:
                made = deal(next(res), value)
            except StopIteration:
                made = None
            else:
                try:
                    made2 = res.send(tp.cast(T, made))
                    if made2 is True:
                        value = made
                    made = made2
                except StopIteration:
                    pass

            return deal(made, value)
        finally:
            res.close()

    def _invoke_func(
        self, value: tp.Any, want: tp.Type, meta: Meta, converter: cattrs.Converter
    ) -> ConvertResponse[T]:
        if len(self.signature.parameters) == 0:
            return tp.cast(ConvertDefinitionNoValue, self.func)()

        elif len(self.signature.parameters) == 1:
            return tp.cast(ConvertDefinitionValue, self.func)(value)

        elif len(self.signature.parameters) == 2 and all(
            v.kind is inspect.Parameter.POSITIONAL_ONLY for v in self.signature.parameters.values()
        ):
            return tp.cast(ConvertDefinitionValueAndType, self.func)(value, want)

        else:
            args = _ArgsExtractor(self.signature, value, want, meta, converter).extract()
            return self.func(*args)


Creator: tp.TypeAlias = tp.Callable[[tp.Type[T]], CreatorDecorator[T]]
