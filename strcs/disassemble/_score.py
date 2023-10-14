import typing as tp

import attrs

if tp.TYPE_CHECKING:
    from ._base import Type


def _get_type() -> type["Type"]:
    from ._base import Type

    return Type


@attrs.define(order=True)
class ScoreOrigin:
    """
    A container used by :class:`strcs.Score` for data related to the MRO of a type
    """

    # The order of the fields matter
    custom: bool = attrs.field(init=False)
    "Whether this class is user defined (True) or standard library (False), decided by whether the module is 'builtins'"

    package: str
    "The package this comes from"

    module: str
    "The module this comes from"

    name: str
    "The name of the class"

    def __attrs_post_init__(self) -> None:
        self.custom = self.module != "builtins"

    @classmethod
    def create(self, typ: type) -> "ScoreOrigin":
        """
        Used to create a ScoreOrigin from a python type.
        """
        return ScoreOrigin(
            name=typ.__name__, module=typ.__module__, package=getattr(typ, "__package__", "")
        )

    def for_display(self, indent="") -> str:
        """
        Return a human friendly string representing this ScoreOrigin.
        """

        def with_space(o: object) -> str:
            s = str(o)

            if s:
                return f" {s}"
            else:
                return ""

        lines = [
            f"custom:{with_space(self.custom)}",
            f"name:{with_space(self.name)}",
            f"module:{with_space(self.module)}",
            f"package:{with_space(self.package)}",
        ]
        return "\n".join(f"{indent}{line}" for line in lines)


@attrs.define(order=True)
class Score:
    """
    A score is a representation of the complexity of a type. The more data held by this object,
    the more complex the type is.

    The order of these fields indicate how important they are in determining whether any
    type is more complex than another.
    """

    type_alias_name: str
    "Name provided to the type if it's a ``typing.NewType`` object"

    # The order of the fields matter
    annotated_union: tuple["Score", ...] = attrs.field(init=False)
    """
    If this object is an annotated union, then annotated_union will contain the scores of each part of the union instead of self.union

    This is so that an optional union with an annotation is considered more complex than one without an annotation
    """

    union_optional: bool = attrs.field(init=False)
    "Whether this is a union that contains a None"

    union_length: int = attrs.field(init=False)
    "How many items are in the union"

    union: tuple["Score", ...]
    "The scores of each part that makes up the union, or empty if not a union or is an annotated union"

    annotated: bool
    "Whether this type is annotated"

    custom: bool = attrs.field(init=False)
    "Whether this type is user defined"

    optional: bool
    "Whether this type is optional"

    mro_length: int = attrs.field(init=False)
    "How many items are in the mro of the type"

    typevars_length: int = attrs.field(init=False)
    "How many type vars are defined for the type if it is a generic"

    typevars_filled: tuple[bool, ...]
    "A boolean in order for each type var saying whether that type var has a value or not"

    typevars: tuple["Score", ...]
    "A score for each type var on the type"

    origin_mro: tuple[ScoreOrigin, ...]
    "A score origin for each object in the mro of the type"

    @classmethod
    def create(cls, typ: "Type") -> "Score":
        """
        Used to create a score for a given :class:`strcs.Type`. This is used by the ``score`` property on the :class:`strcs.Type` object.
        """
        return cls(
            type_alias_name=(
                "" if (alias := typ.type_alias) is None else getattr(alias, "__name__", "")
            ),
            union=tuple(ut.score for ut in typ.nonoptional_union_types),
            typevars=tuple(tv.score for tv in typ.mro.all_vars),
            typevars_filled=tuple(tv is not _get_type().Missing for tv in typ.mro.all_vars),
            optional=typ.optional,
            annotated=typ.is_annotated,
            origin_mro=tuple(ScoreOrigin.create(t) for t in typ.origin_type.__mro__),
        )

    def __attrs_post_init__(self) -> None:
        self.custom = False if not self.origin_mro else self.origin_mro[0].custom
        self.union_length = len(self.union)
        self.union_optional = bool(self.union) and self.optional
        self.mro_length = len(self.origin_mro)
        self.typevars_length = len(self.typevars)

        if self.annotated and self.union:
            self.annotated_union = self.union
            self.union = ()
        else:
            self.annotated_union = ()

    def for_display(self, indent="  ") -> str:
        """
        Return a human readable string representing the score.
        """
        lines: list[str] = []

        class WithDisplay(tp.Protocol):
            def for_display(self, indent="") -> str:
                ...

        def extend(displayable: WithDisplay, extra: tp.Callable[[int], str]) -> None:
            for i, line in enumerate(displayable.for_display(indent=indent).split("\n")):
                lines.append(f"{extra(i)}{line}")

        if self.type_alias_name:
            lines.append(f"✓ type alias: {self.type_alias_name}")

        if self.annotated_union:
            lines.append("✓ Annotated Union:")
            for score in self.union or self.annotated_union:
                extend(score, lambda i: "  *" if i == 0 else "   ")

        if self.union_optional:
            lines.append("✓ Union optional")
        else:
            lines.append("x Union optional")

        if self.union_length:
            lines.append(f"{self.union_length} Union length")

        if self.union:
            lines.append("✓ Union:")
            for score in self.union or self.annotated_union:
                extend(score, lambda i: "  *" if i == 0 else "   ")

        if not self.annotated_union and not self.union:
            lines.append("x Union")

        if self.annotated:
            lines.append("✓ Annotated")
        else:
            lines.append("x Annotated")

        lines.append(f"{self.typevars_length} typevars {self.typevars_filled}")

        if self.typevars:
            lines.append("✓ Typevars:")
            for score in self.typevars:
                extend(score, lambda i: "  *" if i == 0 else "   ")
        else:
            lines.append("x Typevars")

        if self.optional:
            lines.append("✓ Optional")
        else:
            lines.append("x Optional")

        lines.append(f"{self.mro_length} MRO length")

        if self.origin_mro:
            lines.append("✓ Origin MRO:")
            for origin in self.origin_mro:
                extend(origin, lambda i: "  *" if i == 0 else "   ")
        else:
            lines.append("x Origin MRO")

        return "\n".join(f"{indent}{line}" for line in lines)
