import functools
import operator
import typing as tp

import attrs

from ..errors import NotValidType
from ..standard import union_types
from ._instance_check import InstanceCheckMeta

if tp.TYPE_CHECKING:
    from ._base import Type
    from ._cache import TypeCache

    VarCollection = tuple[Type | type[Type.Missing], ...]


@attrs.define
class Distilled:
    original: object
    is_valid: bool
    as_generic: object | None = None
    new_type_path: list[tp.NewType] | None = None

    @property
    def classinfo(self) -> type | tuple[type, ...]:
        if not self.is_valid:
            raise NotValidType()
        return tp.cast(type | tuple[type, ...], self.original)

    @property
    def as_tuple(self) -> tuple[type, ...]:
        classinfo = self.classinfo
        if not isinstance(classinfo, tuple):
            return (classinfo,)
        else:
            return classinfo

    @classmethod
    def valid(
        cls,
        original: object,
        *,
        new_type_path: list[tp.NewType] | None = None,
        as_generic: object | None = None,
    ) -> "Distilled":
        return cls(
            original=original,
            is_valid=True,
            new_type_path=new_type_path or None,
            as_generic=as_generic,
        )

    @classmethod
    def invalid(
        cls,
        original: object,
        *,
        new_type_path: list[tp.NewType] | None = None,
        as_generic: object | None = None,
    ) -> "Distilled":
        return cls(
            original=original,
            is_valid=False,
            new_type_path=new_type_path or None,
            as_generic=as_generic,
        )

    @classmethod
    def create(
        cls,
        classinfo: object,
        *,
        new_type_path: list[tp.NewType] | None = None,
        as_generic: object | None = None,
        comparer: "Comparer",
        _chain: list[object] | None = None,
    ) -> "Distilled":
        from ._base import Type

        if _chain is None:
            _chain = []
        else:
            _chain = list(_chain)

        if new_type_path is None:
            new_type_path = []
        else:
            new_type_path = list(new_type_path)

        if classinfo in _chain:
            return cls.invalid(classinfo)

        optional: bool = False

        while (
            issubclass(classinfo_type := type(classinfo), (InstanceCheckMeta, Type, tp.NewType))
            or tp.get_origin(classinfo) is tp.Annotated
        ):
            if issubclass(classinfo_type, InstanceCheckMeta):
                assert hasattr(classinfo, "Meta")
                assert hasattr(classinfo.Meta, "original")
                optional = optional or classinfo.Meta.optional
                classinfo = classinfo.Meta.original
            elif issubclass(classinfo_type, Type):
                assert hasattr(classinfo, "extracted")
                assert hasattr(classinfo, "optional")
                optional = optional or classinfo.optional
                classinfo = classinfo.extracted
            elif tp.get_origin(classinfo) is tp.Annotated:
                args = tp.get_args(classinfo)
                assert len(args) > 0
                classinfo = args[0]
            elif issubclass(classinfo_type, tp.NewType):
                assert isinstance(classinfo, tp.NewType)
                new_type_path.append(classinfo)
                classinfo = classinfo.__supertype__

        if classinfo is None:
            return cls.valid(type(None), new_type_path=new_type_path, as_generic=as_generic)

        disassembled = comparer.type_cache.disassemble(classinfo)
        optional = optional or disassembled.optional
        _chain.append(classinfo)

        as_generic: object | None = None

        if disassembled.is_union:
            classinfo = disassembled.nonoptional_union_types
        elif disassembled.mro.all_vars:
            as_generic = disassembled.extracted
            if (
                issubclass(type(as_generic), (InstanceCheckMeta, Type))
                or tp.get_origin(as_generic) is tp.Annotated
            ):
                as_generic = cls.create(
                    as_generic, new_type_path=new_type_path, comparer=comparer, _chain=list(_chain)
                ).as_generic
            classinfo = disassembled.origin
        elif isinstance(classinfo, tuple) and type(None) in classinfo:
            classinfo = tuple(part for part in classinfo if part is not type(None))
            if len(classinfo) == 1:
                classinfo = classinfo[0]
        elif type(classinfo) in union_types:
            classinfo = tp.get_args(classinfo)

        result: object

        if isinstance(classinfo, tuple):
            found = tuple(
                cls.create(
                    part,
                    comparer=comparer,
                    new_type_path=new_type_path,
                    as_generic=as_generic,
                    _chain=_chain,
                )
                for part in classinfo
            )

            flat: list[object] = []

            def expand(got: object) -> None:
                if isinstance(got, tuple):
                    for part in got:
                        if part not in flat:
                            expand(part)
                elif got is not None:
                    flat.append(got)

            is_valid = all(part.is_valid for part in found)

            expand(tuple(part.original for part in found))
            result = flat[0] if len(flat) == 1 else tuple(flat)

            if any(part.as_generic for part in found):
                flat.clear()
                expand(tuple(part.as_generic or part.original for part in found))
                as_generic = flat[0] if len(flat) == 1 else functools.reduce(operator.or_, flat)
        else:
            checkable = getattr(classinfo, "checkable", classinfo)
            Meta = getattr(checkable, "Meta", None)
            if Meta and (extracted := getattr(Meta, "extracted", None)) is not None:
                classinfo = extracted

            if not isinstance(classinfo, type):
                distilled = cls.create(
                    classinfo,
                    comparer=comparer,
                    new_type_path=new_type_path,
                    as_generic=as_generic,
                    _chain=_chain,
                )
                result = distilled.original
                is_valid = distilled.is_valid
                as_generic = distilled.as_generic
            else:
                result = classinfo
                is_valid = True
                distilled = cls.valid(classinfo, as_generic=as_generic)

        if is_valid:
            if tp.get_origin(as_generic) in union_types:
                as_generic = functools.reduce(
                    operator.or_,
                    sorted(
                        tp.get_args(as_generic),
                        key=lambda part: comparer.type_cache.disassemble(part).score,
                    ),
                )
            if isinstance(classinfo, tuple):
                classinfo = tuple(
                    sorted(
                        tp.get_args(classinfo),
                        key=lambda part: comparer.type_cache.disassemble(part).score,
                    )
                )

        if isinstance(result, tuple) and type(None) in result:
            optional = True

        if optional and result not in (None, type(None)):
            if not isinstance(result, tuple):
                result = (result, type(None))
            else:
                result = tuple(part for part in result if part is not type(None))
                result = tuple((*result, type(None)))

        if optional and as_generic is not None and is_valid:
            as_generic = tp.Optional[as_generic]

        return cls(
            original=result,
            as_generic=as_generic,
            new_type_path=new_type_path or None,
            is_valid=is_valid,
        )


class _ClassInfo:
    """
    Used to do isinstance and issubclass checks against the underlying types of some object.
    """

    @classmethod
    def create(cls, classinfo: object, comparer: "Comparer"):
        comparing_all_vars = comparer.type_cache.disassemble(classinfo).mro.all_vars
        distilled = comparer.distill(classinfo)
        return cls(
            _comparer=comparer,
            _comparing_all_vars=comparing_all_vars,
            _compare_to=distilled,
        )

    def __init__(
        self,
        *,
        _comparer: "Comparer",
        _comparing_all_vars: "VarCollection",
        _compare_to: Distilled,
    ):
        self.comparer = _comparer
        self.compare_to = _compare_to
        self.comparing_all_vars = _comparing_all_vars

    def isinstance(self, obj: object) -> bool:
        compare_to = self.compare_to
        if compare_to in (None, type(None)) and obj is None:
            return True
        if not compare_to.is_valid:
            return False
        return isinstance(obj, compare_to.classinfo)

    def issubclass(self, comparing: object, *, all_vars: "VarCollection") -> bool:
        compare_to = self.compare_to
        if not compare_to.is_valid:
            return False

        distilled = self.comparer.distill(comparing)
        if not distilled.is_valid:
            return False

        as_type = distilled.original
        if isinstance(as_type, tuple) and len(as_type) == 2 and as_type[1] is type(None):
            as_type = as_type[0]

        if not isinstance(as_type, type):
            return False

        if not issubclass(as_type, compare_to.as_tuple):
            return False

        if all_vars:
            from ._base import Type

            w: object
            g: object

            for w, g in zip(self.comparing_all_vars, all_vars):
                if w is Type.Missing or g is Type.Missing:
                    continue

                if hasattr(w, "checkable"):
                    w = w.checkable
                if hasattr(g, "checkable"):
                    g = g.checkable

                if issubclass(type(w), type) and issubclass(type(g), type):
                    if not issubclass(g, w):
                        return False

        if len(compare_to.new_type_path or []) < len(distilled.new_type_path or []):
            return False

        for cdt, cd in zip(
            reversed(compare_to.new_type_path or []), reversed(distilled.new_type_path or [])
        ):
            if cdt != cd:
                return False

        return True


class Comparer:
    """
    Used to do matching, issubclass and isinstance between different objects.

    An instance of this is created and stored on :class:`strcs.TypeCache` objects.

    This object is used by the :class:`strcs.InstanceCheck` objects.
    """

    def __init__(self, type_cache: "TypeCache"):
        self.type_cache = type_cache

    def distill(self, classinfo: object) -> Distilled:
        return Distilled.create(classinfo, comparer=self)

    def issubclass(self, comparing: object, comparing_to: object) -> bool:
        all_vars = self.type_cache.disassemble(comparing).mro.all_vars
        return _ClassInfo.create(comparing_to, self).issubclass(comparing, all_vars=all_vars)

    def isinstance(self, obj: object, comparing_to: object) -> bool:
        return _ClassInfo.create(comparing_to, self).isinstance(obj)

    def matches(
        self,
        checking: object,
        check_against: object,
        subclasses: bool = False,
        allow_missing_typevars: bool = False,
    ) -> bool:
        chck = self.distill(checking)
        chck_against = self.distill(check_against)

        if chck_against.is_valid and (chck.original == () or not chck.is_valid):
            if subclasses:
                return isinstance(chck.original, chck_against.classinfo)
            else:
                against = chck_against.original
                if not isinstance(against, tuple):
                    against = (against,)
                return type(chck.original) in against

        if not chck.is_valid:
            return chck.classinfo == chck_against.classinfo

        chck_type = chck.as_generic or chck.original
        if isinstance(chck_type, tuple) and chck_type:
            if all(isinstance(part, type) for part in chck_type):
                chck_type = functools.reduce(operator.or_, chck_type)
            elif len(chck_type) == 2 and chck_type[1] in (None, type(None)):
                chck_type = tp.Optional[self.type_cache.disassemble(chck_type[0]).checkable]

        chck_against_type = chck_against.as_generic or chck_against.original
        if isinstance(chck_against_type, tuple) and chck_against_type:
            if all(isinstance(part, type) for part in chck_against_type):
                chck_against_type = functools.reduce(operator.or_, chck_against_type)
            elif len(chck_against_type) == 2 and chck_against_type[1] in (None, type(None)):
                chck_against_type = tp.Optional[
                    self.type_cache.disassemble(chck_against_type[0]).checkable
                ]

        check_against = self.type_cache.disassemble(chck_against_type)
        checking = self.type_cache.disassemble(chck_type)

        if (
            check_against.is_union
            or checking.is_union
            or check_against.optional
            or checking.optional
        ):
            if check_against.optional and checking in (None, type(None)):
                return True

            checking_types: tuple[object, ...]
            check_against_types: tuple[object, ...]

            if not checking.is_union:
                checking_types = (checking,)
            else:
                checking_types = checking.nonoptional_union_types

            if not check_against.is_union:
                check_against_types = (check_against,)
            else:
                check_against_types = check_against.nonoptional_union_types

            return self._matches_union(
                checking_types,
                check_against_types,
                subclasses=subclasses,
                allow_missing_typevars=allow_missing_typevars,
            )
        else:
            return self._matches_single(
                checking,
                check_against,
                subclasses=subclasses,
                allow_missing_typevars=allow_missing_typevars,
            )

    def _matches_union(
        self,
        checking: tuple[object, ...],
        check_against: tuple[object, ...],
        subclasses: bool = False,
        allow_missing_typevars=False,
    ) -> bool:
        if type(None) in checking and type(None) not in check_against:
            return False

        for typ in checking:
            if typ is type(None):
                continue
            if not any(
                self._matches_single(
                    typ,
                    check_against_typ,
                    subclasses=subclasses,
                    allow_missing_typevars=allow_missing_typevars,
                )
                for check_against_typ in check_against
            ):
                return False

        return True

    def _matches_single(
        self,
        matching: object,
        matching_to: object,
        subclasses: bool = False,
        allow_missing_typevars=False,
    ) -> bool:
        from ._base import Type

        matching_dis = self.type_cache.disassemble(matching)
        matching_to_dis = self.type_cache.disassemble(matching_to)

        def match_all_vars(
            matching_vars: "VarCollection", matching_to_vars: "VarCollection"
        ) -> bool:
            for mtv, mttv in zip(
                matching_vars,
                matching_to_vars,
            ):
                if isinstance(mtv, Type) and isinstance(mttv, Type):
                    if not self.matches(mtv, mttv, subclasses=subclasses):
                        return False
                elif mtv is Type.Missing and not allow_missing_typevars:
                    return False
            return True

        if subclasses:
            if not self.issubclass(matching, matching_to):
                return False
        else:
            if not (
                (matching_dis.fields_from == matching_to_dis.fields_from)
                or (
                    type(self.distill(matching_dis.fields_from).original)
                    == matching_to_dis.fields_from
                )
            ):
                return False

        for mtv, mttv in zip(
            matching_dis.mro.all_vars,
            matching_to_dis.mro.all_vars,
        ):
            if isinstance(mtv, Type) and isinstance(mttv, Type):
                if not self.matches(mtv, mttv, subclasses=subclasses):
                    return False
            elif mtv is Type.Missing and mttv is not Type.Missing and not allow_missing_typevars:
                return False

        return True
