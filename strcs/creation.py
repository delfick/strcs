import collections.abc
import typing as tp

import attrs
import cattrs

from .disassemble import Type
from .not_specified import NotSpecified

T = tp.TypeVar("T")


def fill(want: Type[T], res: object) -> tp.Mapping[str, object]:
    if res is NotSpecified:
        res = {}

    if not isinstance(res, collections.abc.MutableMapping):
        raise ValueError(f"Can only fill mappings, got {type(res)}")

    for field in want.fields:
        if field.disassembled_type is not None and field.name not in res:
            if field.disassembled_type.is_annotated or field.disassembled_type.has_fields:
                res[field.name] = NotSpecified

    return res


def instantiate(want: Type[T], res: object, converter: cattrs.Converter) -> T:
    if res is None:
        if want.optional or want.original is None:
            return tp.cast(T, None)

        raise ValueError("Can't instantiate object with None")

    instantiator = want.extracted
    if not callable(instantiator):
        raise TypeError(f"Unsure how to instantiate a {type(instantiator)}: {instantiator}")

    res = fill(want, res)

    conv_obj: dict[str, object] = {}
    for field in want.fields:
        if isinstance(instantiator, type) and field.owner != instantiator:
            continue

        name = field.name

        if name not in res:
            continue

        val = res[name]
        attribute = tp.cast(attrs.Attribute, field)
        conv_obj[name] = converter._structure_attribute(attribute, val)

    return instantiator(**conv_obj)
