import dataclasses
import inspect
import sys
import typing as tp

import attrs

if tp.TYPE_CHECKING:
    from ._base import Type, TypeCache

T = tp.TypeVar("T")
U = tp.TypeVar("U")


def _get_type() -> type["Type"]:
    from ._base import Type

    return Type


@attrs.define
class Default:
    """
    A callable object used to hold and return some static value
    """

    value: object | None

    def __call__(self) -> object | None:
        return self.value


def kind_name_repr(kind: int) -> str:
    """
    Given an inspect.Parameter object, return a string repr for it's name

    .. code-block:: python

        from strcs.disassemble import kind_name_repr
        import inspect


        assert kind_name_repr(inspect.Parameter.VAR_POSITIONAL) == repr("variadic positional")
    """
    known = (
        inspect.Parameter.KEYWORD_ONLY,
        inspect.Parameter.VAR_POSITIONAL,
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
        inspect.Parameter.POSITIONAL_ONLY,
        inspect.Parameter.KEYWORD_ONLY,
        inspect.Parameter.VAR_KEYWORD,
    )

    for k in known:
        if k.value == kind:
            return repr(k.description)

    return "<UNKNOWN_KIND>"


@attrs.define
class Field(tp.Generic[T]):
    """
    A container representing a single field on a class. Used to replicate the field functionality used in
    attrs and dataclasses.
    """

    name: str
    "The name of the field"

    owner: object
    "The class that was being inspected to make this field"

    disassembled_type: "Type[T]"
    "The type of the field in a :class:`strcs.Type` object"

    kind: int = attrs.field(
        default=inspect.Parameter.POSITIONAL_OR_KEYWORD.value, repr=kind_name_repr
    )
    "The inspect.Parameter kind of the field"

    default: tp.Callable[[], object | None] | None = attrs.field(default=None)
    "A callable returning the default value for the field"

    original_owner: object = attrs.field(default=attrs.Factory(lambda s: s.owner, takes_self=True))
    "The class that originally defined this field"

    def with_replaced_type(self, typ: "Type[U]") -> "Field[U]":
        """
        Return a clone of this field, but with the provided type.
        """
        return Field[U](
            name=self.name,
            owner=self.owner,
            disassembled_type=typ,
            kind=self.kind,
            default=self.default,
            original_owner=self.original_owner,
        )

    @property
    def type(self) -> object:
        """
        Return the original object used to make the :class:`strcs.Type` in the ``disassembled_type`` field.
        """
        return self.disassembled_type.original

    def clone(self) -> "Field[T]":
        """
        Return a clone of this object.
        """
        return self.with_replaced_type(self.disassembled_type)

    @kind.validator
    def check_kind(self, attribute: attrs.Attribute, value: object) -> None:
        allowed = (
            inspect.Parameter.KEYWORD_ONLY,
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.KEYWORD_ONLY,
            inspect.Parameter.VAR_KEYWORD,
        )
        if value not in [a.value for a in allowed]:
            raise ValueError(
                f"Only allow parameter kinds. Got {value}, want one of {', '.join([f'{a.value} ({a.description})' for a in allowed])}"
            )


def fields_from_class(type_cache: "TypeCache", typ: type) -> tp.Sequence[Field]:
    """
    Given some class, return a sequence of :class:`strcs.Field` objects.

    Done by looking at the signature of the object as if it were a callable.
    """
    result: list[Field] = []
    try:
        signature = inspect.signature(typ)
    except ValueError:
        return result

    for name, param in list(signature.parameters.items()):
        field_type = param.annotation
        if param.annotation is inspect.Parameter.empty:
            field_type = object

        if param.kind in (inspect.Parameter.VAR_KEYWORD, inspect.Parameter.VAR_POSITIONAL):
            name = ""

        dflt: tp.Callable[[], object | None] | None = None
        if param.default is not inspect.Parameter.empty:
            dflt = Default(param.default)
        result.append(
            Field(
                name=name,
                owner=typ,
                default=dflt,
                kind=param.kind.value,
                disassembled_type=_get_type().create(field_type, cache=type_cache),
            )
        )

    return result


def fields_from_attrs(type_cache: "TypeCache", typ: type) -> tp.Sequence[Field]:
    """
    Given some attrs type, return a sequence of :class:`strcs.Field` objects.

    Take into account when a field has ``default`` or ``factory`` options.

    Also take into account field aliases, as well as underscore and double underscore prefixed fields.
    """
    result: list[Field] = []
    for field in attrs.fields(typ):
        if not field.init:
            continue

        field_type = field.type
        if field_type is None:
            field_type = object

        kind = inspect.Parameter.POSITIONAL_OR_KEYWORD.value
        if field.kw_only:
            kind = inspect.Parameter.KEYWORD_ONLY.value

        dflt: tp.Callable[[], object | None] | None = None
        if hasattr(field.default, "factory") and callable(field.default.factory):
            if not field.default.takes_self:
                dflt = field.default.factory

        elif field.default is not attrs.NOTHING:
            dflt = Default(field.default)

        if sys.version_info >= (3, 11) and field.alias is not None:
            name = field.alias
        else:
            name = field.name
            if name.startswith("_"):
                name = name[1:]

        if name.startswith(f"{typ.__name__}_"):
            name = name[len(f"{typ.__name__}_") + 1 :]

        result.append(
            Field(
                name=name,
                owner=typ,
                default=dflt,
                kind=kind,
                disassembled_type=_get_type().create(field_type, cache=type_cache),
            )
        )

    return result


def fields_from_dataclasses(type_cache: "TypeCache", typ: type) -> tp.Sequence[Field]:
    """
    Given some dataclasses.dataclass type return a sequence of :class:`strcs.Field` objects.

    Take into account when fields have ``default`` or ``default_factory`` options.
    """
    result: list[Field] = []
    for field in dataclasses.fields(typ):
        if not field.init:
            continue

        field_type = field.type
        if field_type is None:
            field_type = object

        kind = inspect.Parameter.POSITIONAL_OR_KEYWORD.value
        if field.kw_only:
            kind = inspect.Parameter.KEYWORD_ONLY.value

        dflt: tp.Callable[[], object | None] | None = None
        if field.default is not dataclasses.MISSING:
            dflt = Default(field.default)

        if field.default_factory is not dataclasses.MISSING:
            dflt = field.default_factory

        name = field.name
        result.append(
            Field(
                name=name,
                owner=typ,
                default=dflt,
                kind=kind,
                disassembled_type=_get_type().create(field_type, cache=type_cache),
            )
        )
    return result
