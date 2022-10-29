from .meta import Meta, extract_type
from .hints import resolve_types
from . import errors

from cattrs.errors import IterableValidationError
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


ConvertResponseValues: tp.TypeAlias = bool | dict[str, tp.Any] | T
ConvertResponseGenerator: tp.TypeAlias = tp.Generator[
    tp.Optional[ConvertResponseValues[T]], T, None
]

ConvertResponse: tp.TypeAlias = tp.Optional[ConvertResponseValues[T] | ConvertResponseGenerator[T]]

ConvertDefinitionNoValue: tp.TypeAlias = tp.Callable[[], ConvertResponse[T]]
ConvertDefinitionValue: tp.TypeAlias = tp.Callable[[tp.Any], ConvertResponse[T]]
ConvertDefinitionValueAndType: tp.TypeAlias = tp.Callable[[tp.Any, tp.Type], ConvertResponse[T]]
# Also allowed is
# - (Any, Type, /, meta1, meta2, ...)
# - (Any, /, meta1, meta2, ...)
# But python typing is restrictive and you can't express that

ConvertDefinition: tp.TypeAlias = tp.Callable[..., ConvertResponse[T]]
ConvertFunction: tp.TypeAlias = tp.Callable[["CreateArgs"], T]


class WrappedCreator(tp.Generic[T]):
    def __init__(self, wrapped: tp.Callable[["CreateArgs"], T], func: ConvertDefinition[T]):
        self.func = func
        self.wrapped = wrapped

    def __call__(self, create_args: "CreateArgs") -> T:
        return self.wrapped(create_args)

    def __repr__(self):
        return f"<Wrapped {self.func}>"


def take_or_make(value: tp.Any, typ: tp.Type[T], /) -> ConvertResponse[T]:
    if isinstance(value, typ):
        return value
    elif value is NotSpecified or isinstance(value, dict):
        return value
    else:
        return None


def filldict(
    converter: cattrs.Converter, register: "CreateRegister", res: tp.Any, want: tp.Type
) -> tp.Any:
    if isinstance(res, dict) and hasattr(want, "__attrs_attrs__"):
        for field in attrs.fields(want):
            if field.type is not None and field.name not in res:
                if _CreateStructureHook(register, converter, field.type).check_func(field.type):
                    res[field.name] = NotSpecified
    return res


def fromdict(
    converter: cattrs.Converter, register: "CreateRegister", res: tp.Any, want: type[T]
) -> T:
    if res is NotSpecified:
        res = {}
    res = filldict(converter, register, res, want)
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


@tp.runtime_checkable
class _Ann(tp.Protocol[T]):
    def adjusted_meta(self, meta: Meta, typ: tp.Type[T]) -> Meta:
        ...

    def adjusted_creator(
        self, creator: tp.Optional[ConvertFunction[T]], register: "CreateRegister", typ: tp.Type[T]
    ) -> tp.Optional[ConvertFunction[T]]:
        ...


@define(frozen=True)
class FromMeta(_Ann):
    pattern: str

    def adjusted_meta(self, meta: Meta, typ: tp.Type[T]) -> Meta:
        val = meta.retrieve_one(typ, self.pattern)
        return meta.clone(data_override={"retrieved": val})

    def adjusted_creator(
        self, creator: tp.Optional[ConvertFunction], register: "CreateRegister", typ: tp.Type[T]
    ) -> tp.Optional[ConvertFunction[T]]:
        def retrieve(val: tp.Any, /, _meta: Meta) -> ConvertResponse[T]:
            return tp.cast(T, _meta.retrieve_one(object, "retrieved"))

        a = Ann[T](creator=retrieve)
        return a.adjusted_creator(creator, register, typ)


@tp.runtime_checkable
class AdjustableMeta(tp.Protocol):
    def adjusted_meta(self, meta: Meta, typ: tp.Type[T]) -> Meta:
        ...


class Ann(_Ann[T]):
    _func: tp.Optional[ConvertFunction[T]] = None

    def __init__(
        self,
        meta: tp.Optional[Annotation | AdjustableMeta] = None,
        creator: tp.Optional[ConvertDefinition[T]] = None,
    ):
        self.meta = meta
        self.creator = creator

    def adjusted_meta(self, meta: Meta, typ: tp.Type[T]) -> Meta:
        if self.meta is None:
            return meta

        if isinstance(self.meta, AdjustableMeta):
            return self.meta.adjusted_meta(meta, typ)

        if self.meta.merge_meta:
            clone = meta.clone()
            for field in attrs.fields(self.meta.__class__):
                if not field.name.startswith("_"):
                    optional, _ = extract_type(field.type)
                    val = getattr(self.meta, field.name)
                    if not optional or val is not None:
                        clone[field.name] = val
            return clone
        else:
            return meta.clone({"__call_defined_annotation__": self.meta})

    def adjusted_creator(
        self, creator: tp.Optional[ConvertFunction], register: "CreateRegister", typ: tp.Type[T]
    ) -> tp.Optional[ConvertFunction[T]]:
        if self.creator is None:
            return creator

        wrapped, _ = CreatorDecorator(
            register, typ, assume_unchanged_converted=hasattr(typ, "__attrs_attrs__")
        ).wrap(self.creator)

        return wrapped


class Registerer(tp.Protocol[T]):
    def __call__(self, func: tp.Optional[ConvertDefinition[T]] = None) -> ConvertDefinition[T]:
        ...


class Creator(tp.Protocol):
    def __call__(self, typ: tp.Type[T], assume_unchanged_converted=True) -> Registerer[T]:
        ...


class CreateRegister:
    def __init__(
        self,
        *,
        register: None | dict[type[T], ConvertFunction[T]] = None,
        last_meta: None | Meta = None,
        last_type: None | type[T] = None,
        skip_creator: None | ConvertDefinition[T] = None,
        auto_resolve_attrs_and_dataclasses_annotations: bool = True,
    ):
        if register is None:
            register = {}
        self.register = register
        self.last_meta = last_meta
        self.last_type = last_type
        self.skip_creator = skip_creator
        self.auto_resolve_attrs_and_dataclasses_annotations = (
            auto_resolve_attrs_and_dataclasses_annotations
        )

    def clone(
        self, last_meta: Meta, last_type: type[T], skip_creator: ConvertDefinition[T]
    ) -> "CreateRegister":
        return type(self)(
            register=self.register,
            last_meta=last_meta,
            last_type=last_type,
            skip_creator=skip_creator,
            auto_resolve_attrs_and_dataclasses_annotations=self.auto_resolve_attrs_and_dataclasses_annotations,
        )

    def __setitem__(self, typ: tp.Type[T], creator: ConvertFunction[T]) -> None:
        if not isinstance(typ, type):
            raise errors.CanOnlyRegisterTypes(got=typ)
        self.register[typ] = creator

    def __contains__(self, typ: tp.Type) -> bool:
        return self.creator_for(typ) is not None

    def make_decorator(self) -> Creator:
        def creator(typ: tp.Type[T], assume_unchanged_converted=True) -> Registerer[T]:
            return tp.cast(
                Registerer[T],
                CreatorDecorator(self, typ, assume_unchanged_converted=assume_unchanged_converted),
            )

        return creator

    def creator_for(self, typ: tp.Type[T]) -> tp.Optional[ConvertFunction[T]]:
        origin: tp.Optional[tp.Type[T]] = getattr(typ, "__origin__", None)
        if origin is not None:
            typ = origin

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
        once_only_creator: tp.Optional[ConvertFunction[T]] = None,
    ) -> T:
        return _CreateStructureHook.structure(
            self,
            typ,
            value,
            meta,
            once_only_creator,
            last_meta=self.last_meta,
            last_type=self.last_type,
            skip_creator=self.skip_creator,
        )

    def create_annotated(
        self,
        typ: tp.Type[T],
        ann: tp.Union[Annotation | _Ann | ConvertFunction[T]],
        value: tp.Any = NotSpecified,
        meta: tp.Any = NotSpecified,
        once_only_creator: tp.Optional[ConvertFunction[T]] = None,
    ) -> T:
        return _CreateStructureHook.structure(
            self,
            tp.cast(tp.Type[T], tp.Annotated[typ, ann]),
            value,
            meta,
            once_only_creator,
            last_meta=self.last_meta,
            last_type=self.last_type,
            skip_creator=self.skip_creator,
        )


class _CreateStructureHook:
    @classmethod
    def structure(
        kls,
        register: CreateRegister,
        typ: tp.Type[T],
        value: tp.Any = NotSpecified,
        meta: tp.Any = NotSpecified,
        creator: tp.Optional[ConvertFunction[T]] = None,
        last_meta: None | Meta = None,
        last_type: None | type[T] = None,
        skip_creator: None | ConvertDefinition[T] = None,
    ) -> T:
        if meta is NotSpecified:
            if last_meta is not None:
                meta = last_meta.clone()
            else:
                meta = Meta()

        converter = meta.converter
        hooks = kls(
            register=register,
            converter=converter,
            meta=meta,
            last_meta=last_meta,
            last_type=last_type,
            skip_creator=skip_creator,
            once_only_creator=creator,
        )

        ann, want = hooks._interpret_annotation(typ)

        converter.register_structure_hook_func(hooks.switch_check, hooks.convert)

        try:
            ret = hooks.convert(value, typ)
        finally:
            converter._structure_func._function_dispatch._handler_pairs.remove(
                (hooks.switch_check, hooks.convert, False)
            )

        return ret

    def __init__(
        self,
        register: CreateRegister,
        converter: cattrs.Converter,
        meta: tp.Any = NotSpecified,
        once_only_creator: tp.Optional[ConvertFunction[T]] = None,
        last_meta: None | Meta = None,
        last_type: None | type[T] = None,
        skip_creator: None | ConvertDefinition[T] = None,
    ):
        self.meta = meta
        self.register = register
        self.do_check = True
        self.last_meta = last_meta
        self.last_type = last_type
        self.converter = converter
        self.skip_creator = skip_creator
        self.once_only_creator = once_only_creator
        self.cache: dict[tp.Type[T], ConvertFunction[T]] = {}

    def _interpret_annotation(self, want: tp.Type[T]) -> tp.Tuple[tp.Optional[_Ann], tp.Type[T]]:
        ann: tp.Optional[Annotation | _Ann | ConvertDefinition[T]] = None
        if hasattr(want, "__metadata__"):
            metadata: tp.Tuple[tp.Any] = getattr(want, "__metadata__")
            if metadata and (isinstance(metadata[0], (_Ann, Annotation)) or callable(metadata[0])):
                ann = metadata[0]

                if isinstance(ann, Annotation):
                    ann = Ann(ann)
                elif callable(ann):
                    ann = Ann[T](creator=ann)

                origin = getattr(want, "__origin__", None)
                if origin is not None:
                    want = origin

        return tp.cast(_Ann, ann), want

    def convert(self, value: tp.Any, want: tp.Type[T]) -> T:
        wrapped: tp.Type[T]
        ann, wrapped = self._interpret_annotation(want)

        if not self.check_func(want):
            return self.bypass(value, want)

        meta = self.meta
        creator = self.once_only_creator
        self.once_only_creator = None

        want = wrapped
        if want in self.cache and creator is None:
            creator = self.cache[want]

        if isinstance(ann, AdjustableMeta):
            meta = ann.adjusted_meta(meta, want)
            creator = ann.adjusted_creator(creator, self.register, want)
            if meta is not self.meta:
                return self.register.create(want, value, meta=meta, once_only_creator=creator)

        if creator and creator is not self.skip_creator and getattr(creator, "func", None):
            skip = False
            if self.skip_creator:
                if (
                    creator is self.skip_creator
                    or getattr(creator, "func", None) is self.skip_creator
                ):
                    skip = True

            if not skip:
                return creator(CreateArgs(value, want, meta, self.converter, self.register))

        if isinstance(value, want):
            return value
        else:
            return fromdict(self.converter, self.register, value, want)

    def switch_check(self, want: tp.Type) -> bool:
        if self.register.auto_resolve_attrs_and_dataclasses_annotations:
            resolve_types(want)

        ret = self.do_check
        self.do_check = True
        return ret

    def check_func(self, want: tp.Type) -> bool:
        if self.register.auto_resolve_attrs_and_dataclasses_annotations:
            resolve_types(want)

        ann, want = self._interpret_annotation(want)
        creator = self.register.creator_for(want)

        if creator is not None:
            self.cache[want] = creator
            return True

        return bool(ann or self.once_only_creator or hasattr(want, "__attrs_attrs__"))

    def bypass(self, value: tp.Any, want: tp.Type[T]) -> T:
        self.do_check = False
        self.converter._structure_func.dispatch.cache_clear()
        try:
            value = filldict(self.converter, self.register, value, want)
            return self.converter.structure(value, want)
        except IterableValidationError as e:
            raise errors.FailedToConvertIterable(message=e.message, exceptions=list(e.exceptions))


class _ArgsExtractor:
    def __init__(
        self,
        *,
        signature: inspect.Signature,
        value: tp.Any,
        want: tp.Type,
        meta: Meta,
        creator: ConvertDefinition,
        converter: cattrs.Converter,
        register: CreateRegister,
    ):
        self.meta = meta
        self.want = want
        self.value = value
        self.creator = creator
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

        def provided(param: inspect.Parameter, name: str, typ: tp.Type) -> bool:
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
                use.append(
                    self.register.clone(
                        last_type=self.want, last_meta=self.meta, skip_creator=self.creator
                    )
                )
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
    def __init__(
        self,
        register: CreateRegister,
        typ: tp.Type[T],
        assume_unchanged_converted=True,
    ):
        self.typ = typ
        self.register = register
        self.assume_unchanged_converted = assume_unchanged_converted

    def __call__(self, func: tp.Optional[ConvertDefinition[T]] = None) -> ConvertDefinition[T]:
        wrapped, func = self.wrap(func)
        self.register[self.typ] = wrapped
        return func

    def wrap(
        self, func: tp.Optional[ConvertDefinition[T]] = None
    ) -> tp.Tuple[ConvertFunction[T], ConvertDefinition[T]]:
        if func is None:
            self.func = tp.cast(ConvertDefinition[T], take_or_make)
        else:
            self.func = tp.cast(ConvertDefinition[T], func)

        if hasattr(self.func, "side_effect"):
            # Hack to deal with mock objects
            self.signature = inspect.signature(self.func.side_effect)  # type: ignore
        else:

            self.signature = inspect.signature(tp.cast(tp.Callable, self.func))

        wrapped = WrappedCreator(self.wrapped, self.func)
        return wrapped, self.func

    def wrapped(self, create_args: CreateArgs) -> T:
        want = create_args.want
        meta = create_args.meta
        value = create_args.value
        register = create_args.register
        converter = create_args.converter

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
            args = _ArgsExtractor(
                signature=self.signature,
                value=value,
                want=want,
                meta=meta,
                converter=converter,
                register=register,
                creator=self.func,
            ).extract()
            return self.func(*args)
