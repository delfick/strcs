"""
A key part of what ``strcs`` provides is the ability to provide functions that
are used to transform between some value and the final type. These functions
allow the developer to request information necessary for that transformation from
the meta object that is present.

The ``ArgsExtractor`` is used to determine the information that is passed into
these functions. It takes in information about the function, as well as some
related information and returns what the function should be called with.
"""
import inspect
import typing as tp

import cattrs

from .disassemble import Type
from .meta import Meta

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
        """
        Looking at the signature object of the function we want to generate values
        for, we can determine what to provide.

        Support all the ConvertDefinition forms:

        ()

        (value, /)

        (value, want, /)

        (value, want, /, **meta)

        Where meta objects can be:

        _meta: The meta object
        _converter: The cattrs.Converter object
        _register: The CreateRegister object

        Search in meta by name only if a keyword arg has no type annotation and
        search in meta by name and type if a keyword arg does have a type
        annotation.
        """
        from .register import CreateRegister

        values = list(self.signature.parameters.values())

        if len(values) < 2 and all(v.kind is inspect.Parameter.POSITIONAL_ONLY for v in values):
            return [self.value, self.want][: len(values)]

        use = []

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
                use.append(
                    self.meta.retrieve_one(
                        object,
                        param.name,
                        default=param.default,
                        type_cache=self.register.type_cache,
                    )
                )
            else:
                use.append(
                    self.meta.retrieve_one(
                        param.annotation,
                        param.name,
                        default=param.default,
                        type_cache=self.register.type_cache,
                    )
                )

        return use
