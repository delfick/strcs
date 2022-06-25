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
ConvertResponseGenerator: tp.TypeAlias = tp.Generator[ConvertResponseValues | T, T, None]

ConvertResponse: tp.TypeAlias = ConvertResponseValues | ConvertResponseGenerator[T] | T

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
            if field.type is not None and field.name not in res:
                if _CreateStructureHook(register, converter, field.type).check_func(field.type):
                    res[field.name] = NotSpecified
    return converter.structure_attrs_fromdict(tp.cast(dict, res), want)


@define
class Annotation:
    @property
    def merge_meta(self) -> bool:
        return False


@define
class MergedAnnotation(Annotation):
    @property
    def merge_meta(self) -> bool:
        return True


class _Ann(tp.Protocol):
    def adjusted_meta(self, meta: Meta, typ: tp.Type) -> Meta:
        ...

    def adjusted_creator(
        self, creator: ConvertFunction, register: "CreateRegister", typ: tp.Type[T]
    ) -> ConvertFunction[T]:
        ...


@define(frozen=True)
class FromMeta(_Ann):
    pattern: str

    def adjusted_meta(self, meta: Meta, typ: tp.Type) -> Meta:
        val = meta.retrieve_one(typ, self.pattern)
        return meta.clone(data_override={"retrieved": val})

    def adjusted_creator(
        self, creator: ConvertFunction, register: "CreateRegister", typ: tp.Type[T]
    ) -> ConvertFunction[T]:
        def retrieve(val: tp.Any, /, retrieved: typ) -> typ:
            return retrieved

        return Ann(creator=retrieve).adjusted_creator(creator, register, typ)


class Ann(_Ann):
    _func: tp.Optional[ConvertFunction] = None

    def __init__(
        self, meta: tp.Optional[Annotation] = None, creator: tp.Optional[ConvertFunction] = None
    ):
        self.meta = meta
        self.creator = creator

    def adjusted_meta(self, meta: Meta, typ: tp.Type) -> Meta:
        if self.meta is None:
            return meta

        if hasattr(self.meta, "adjusted_meta"):
            return self.meta.adjusted_meta(meta, typ)

        if self.meta.merge_meta:
            clone = meta.clone()
            for field in attrs.fields(self.meta.__class__):
                if not field.name.startswith("_"):
                    clone[field.name] = getattr(self.meta, field.name)
            return clone
        else:
            return meta.clone({"__call_defined_annotation__": self.meta})

    def adjusted_creator(
        self, creator: ConvertFunction, register: "CreateRegister", typ: tp.Type[T]
    ) -> ConvertFunction[T]:
        if self.creator is None:
            return creator

        return CreatorDecorator(
            register,
            typ,
            assume_unchanged_converted=hasattr(typ, "__attrs_attrs__"),
            return_wrapped=True,
        )(self.creator)


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

    def create(
        self,
        typ: tp.Type[T],
        value: tp.Any = NotSpecified,
        meta: tp.Any = NotSpecified,
        creator: tp.Optional[ConvertFunction[T]] = None,
    ):
        return _CreateStructureHook.structure(self, typ, value, meta, creator)


class _CreateStructureHook:
    @classmethod
    def structure(
        kls,
        register: CreateRegister,
        typ: tp.Type[T],
        value: tp.Any = NotSpecified,
        meta: tp.Any = NotSpecified,
        creator: tp.Optional[ConvertFunction[T]] = None,
    ) -> T:
        if meta is NotSpecified:
            meta = Meta()

        converter = cattrs.Converter()
        hooks = kls(register, converter, typ, value, meta, creator)
        converter.register_structure_hook_func(hooks.check_func, hooks.convert)
        if hooks.check_func(typ):
            return hooks.convert(value, typ)
        else:
            return converter.structure(value, typ)

    def __init__(
        self,
        register: CreateRegister,
        converter: cattrs.Converter,
        typ: tp.Type[T],
        value: tp.Any = NotSpecified,
        meta: tp.Any = NotSpecified,
        creator: tp.Optional[ConvertFunction[T]] = None,
    ):
        self.typ = typ
        self.meta = meta
        self.value = value
        self.creator = creator
        self.register = register
        self.converter = converter
        self.cache: dict[tp.Type[T], ConvertFunction[T]] = {}

    def _interpret_annotation(
        self, want: tp.Type, dive_into_lists=False
    ) -> tp.Tuple["_Ann", tp.Type[T]]:
        ann: tp.Optional[Annotation | _Ann | ConvertFunction] = None
        if hasattr(want, "__origin__"):
            if want.__origin__ is not list:
                ann = want.__metadata__[0]

                if isinstance(ann, Annotation):
                    ann = Ann(ann)
                elif callable(ann):
                    ann = Ann(creator=ann)

                want = want.__origin__

                if dive_into_lists and hasattr(want, "__origin__"):
                    if want.__origin__ is list and len(want.__args__) == 1:
                        want = want.__args__[0]

        return ann, want

    def convert(self, value: tp.Any, want: tp.Type[T]) -> T:
        meta = self.meta
        creator = self.creator

        ann, want = self._interpret_annotation(want)

        if want in self.cache and creator is None:
            creator = self.cache[want]

        if ann:
            meta = ann.adjusted_meta(meta, want)
            creator = ann.adjusted_creator(creator, self.register, want)
            if meta is not self.meta:
                return self.register.create(want, value, meta=meta, creator=creator)

        if creator:
            return creator(CreateArgs(value, want, meta, self.converter, self.register))
        elif isinstance(value, want):
            return value
        else:
            return fromdict(self.converter, self.register, value, want)

    def check_func(self, want: tp.Type[T]) -> bool:
        ann, want = self._interpret_annotation(want, dive_into_lists=True)
        creator = self.register.creator_for(want)

        if creator is not None:
            self.cache[want] = creator
            return True

        return ann or self.creator or hasattr(want, "__attrs_attrs__")


class _ArgsExtractor:
    def __init__(
        self,
        signature: inspect.Signature,
        value: tp.Any,
        want: tp.Type,
        meta: Meta,
        converter: cattrs.Converter,
        register: CreateRegister,
    ):
        self.meta = meta
        self.want = want
        self.value = value
        self.register = register
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

        def provided(param: inspect.Parameter, name: str, typ: tp.Type[T]) -> T:
            if param.name != name:
                return False

            if param.annotation is inspect._empty:
                return True

            if isinstance(param.annotation, type) and issubclass(param.annotation, typ):
                return True

            return False

        for param in values:
            if provided(param, "_meta", Meta):
                use.append(self.meta)
            elif provided(param, "_converter", cattrs.Converter):
                use.append(self.converter)
            elif provided(param, "_register", CreateRegister):
                use.append(self.register)
            elif param.annotation in (inspect._empty, tp.Any):
                use.append(self.meta.retrieve_one(object, param.name, default=param.default))
            else:
                use.append(
                    self.meta.retrieve_one(param.annotation, param.name, default=param.default)
                )

        return use


@define
class CreateArgs:
    value: tp.Any
    want: tp.Type
    meta: Meta
    converter: cattrs.Converter
    register: CreateRegister


class CreatorDecorator(tp.Generic[T]):
    func: ConvertDefinition[T]

    def __init__(
        self,
        register: CreateRegister,
        typ: tp.Type[T],
        assume_unchanged_converted=True,
        return_wrapped=False,
    ):
        self.typ = typ
        self.register = register
        self.return_wrapped = return_wrapped
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

        if self.return_wrapped:
            return self.wrapped
        else:
            self.register[self.typ] = self.wrapped
            return self.func

    def wrapped(self, create_args: CreateArgs) -> T:
        value = create_args.value
        want = create_args.want
        meta = create_args.meta
        converter = create_args.converter
        register = create_args.register

        if self.assume_unchanged_converted and isinstance(value, want):
            return value

        res = self._invoke_func(value, want, meta, converter, register)

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
        self,
        value: tp.Any,
        want: tp.Type,
        meta: Meta,
        converter: cattrs.Converter,
        register: CreateRegister,
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
            args = _ArgsExtractor(self.signature, value, want, meta, converter, register).extract()
            return self.func(*args)


Creator: tp.TypeAlias = tp.Callable[[tp.Type[T]], CreatorDecorator[T]]
