import typing as tp

import attrs

if tp.TYPE_CHECKING:
    from ._base import Type


def _get_type() -> type["Type"]:
    from ._base import Type

    return Type


@attrs.define(order=True)
class ScoreOrigin:
    # The order of the fields matter
    custom: bool = attrs.field(init=False)
    package: str
    module: str
    name: str

    def __attrs_post_init__(self) -> None:
        self.custom = self.module != "builtins"

    @classmethod
    def create(self, typ: type) -> "ScoreOrigin":
        return ScoreOrigin(
            name=typ.__name__, module=typ.__module__, package=getattr(typ, "__package__", "")
        )

    def for_display(self, indent="") -> str:
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
    # The order of the fields matter
    annotated_union: tuple["Score", ...] = attrs.field(init=False)
    union_optional: bool = attrs.field(init=False)
    union_length: int = attrs.field(init=False)
    union: tuple["Score", ...]
    annotated: bool
    custom: bool = attrs.field(init=False)
    optional: bool
    mro_length: int = attrs.field(init=False)
    typevars_length: int = attrs.field(init=False)
    typevars_filled: tuple[bool, ...]
    typevars: tuple["Score", ...]
    origin_mro: tuple[ScoreOrigin, ...]

    @classmethod
    def create(cls, typ: "Type") -> "Score":
        return cls(
            union=tuple(ut.score for ut in typ.nonoptional_union_types),
            typevars=tuple(tv.score for tv in typ.mro.all_vars),
            typevars_filled=tuple(tv is not _get_type().Missing for tv in typ.mro.all_vars),
            optional=typ.optional,
            annotated=typ.is_annotated,
            origin_mro=tuple(ScoreOrigin.create(t) for t in typ.origin.__mro__),
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
        lines: list[str] = []

        class WithDisplay(tp.Protocol):
            def for_display(self, indent="") -> str:
                ...

        def extend(displayable: WithDisplay, extra: tp.Callable[[int], str]) -> None:
            for i, line in enumerate(displayable.for_display(indent=indent).split("\n")):
                lines.append(f"{extra(i)}{line}")

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
