import typing as tp
from collections.abc import MutableMapping

import attrs
import cattrs

from ..not_specified import NotSpecified
from ._base import Type

T = tp.TypeVar("T")


def fill(want: Type[T], res: object) -> tp.Mapping[str, object]:
    """
    Given a :class:`strcs.Type` and some object, ensure the object has ``NotSpecified`` as values for
    any missing key that we want to go through :class:`strcs` logic.

    If res is :class:`strcs.NotSpecified` it will be replaced with a dictionary. If it otherwise isn't a
    mutable mapping, then this function currently will complain.

    The way ``strcs`` integrates with ``cattrs`` means that keys with no value may not go through
    all the logic we want it to go through, and so if the type of the field is annotated or
    "has_fields" then that missing key will be given a :class:`strcs.NotSpecified`.
    """
    if res is NotSpecified:
        res = {}

    if not isinstance(res, MutableMapping):
        raise ValueError(f"Can only fill mappings, got {type(res)}")

    for field in want.fields:
        if field.disassembled_type is not None and field.name not in res:
            if field.disassembled_type.is_annotated or field.disassembled_type.has_fields:
                res[field.name] = NotSpecified

    return res


def instantiate(want: Type[T], res: object, converter: cattrs.Converter) -> T:
    """
    Given a :class:`strcs.Type` and some object, turn that object into an instance of our type.

    This function will complain if the extracted type is not callable.

    This will find values for keys in res depending on the fields on the provided type that
    are owned by the extracted type.

    It will use the ``cattrs.Converter`` provided to do transformation on each field.
    """
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
