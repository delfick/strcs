import inspect
import typing as tp

import cattrs

from .meta import Meta
from .types import Type

if tp.TYPE_CHECKING:
    from .decorator import ConvertDefinition
    from .register import CreateRegister

T = tp.TypeVar("T")


class ArgsExtractor(tp.Generic[T]):
    def __init__(
        self,
        *,
        signature: inspect.Signature,
        value: object,
        want: Type[T],
        meta: Meta,
        creator: "ConvertDefinition[T]",
        converter: cattrs.Converter,
        register: "CreateRegister",
    ):
        self.meta = meta
        self.want = want
        self.value = value
        self.creator = creator
        self.register = register
        self.converter = converter
        self.signature = signature

    def extract(self) -> list[object]:
        from .register import CreateRegister

        use = []
        values = list(self.signature.parameters.values())

        if values and values[0].kind is inspect.Parameter.POSITIONAL_ONLY:
            values.pop(0)
            use.append(self.value)

        if values and values[0].kind is inspect.Parameter.POSITIONAL_ONLY:
            values.pop(0)
            use.append(self.want)

        def provided(param: inspect.Parameter, name: str, typ: type) -> bool:
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
            elif param.annotation in (inspect._empty, object):
                use.append(self.meta.retrieve_one(object, param.name, default=param.default))
            else:
                use.append(
                    self.meta.retrieve_one(param.annotation, param.name, default=param.default)
                )

        return use
