import functools
import operator
import typing as tp

from ..standard import union_types
from ._instance_check import InstanceCheckMeta

if tp.TYPE_CHECKING:
    from ._base import Type
    from ._cache import TypeCache

    VarCollection = tuple[Type | type[Type.Missing], ...]


class _ClassInfo:
    """
    Used to do isinstance and issubclass checks against the underlying types of some object.
    """

    @classmethod
    def create(cls, classinfo: object, comparer: "Comparer"):
        comparing_all_vars = comparer.type_cache.disassemble(classinfo).mro.all_vars
        classinfo, is_valid_classinfo = comparer.distill(classinfo)
        return cls(
            _comparer=comparer,
            _comparing_all_vars=comparing_all_vars,
            _compare_to=classinfo,
            _is_valid_classinfo=is_valid_classinfo,
        )

    def __init__(
        self,
        *,
        _comparer: "Comparer",
        _comparing_all_vars: "VarCollection",
        _compare_to: object,
        _is_valid_classinfo: bool,
    ):
        self.comparer = _comparer
        self.compare_to = _compare_to
        self.comparing_all_vars = _comparing_all_vars
        self._is_valid_classinfo = _is_valid_classinfo

    def is_valid_classinfo(self, classinfo: object) -> tp.TypeGuard[type]:
        return classinfo is self.compare_to and self._is_valid_classinfo

    def isinstance(self, obj: object) -> bool:
        compare_to = self.compare_to
        if compare_to in (None, type(None)) and obj is None:
            return True
        if not self.is_valid_classinfo(compare_to):
            return False
        return isinstance(obj, compare_to)

    def issubclass(self, comparing: object, *, all_vars: "VarCollection") -> bool:
        compare_to = self.compare_to
        if not self.is_valid_classinfo(compare_to):
            return False

        as_type, _ = self.comparer.distill(comparing)
        if isinstance(as_type, tuple) and len(as_type) == 2 and as_type[1] is type(None):
            as_type = as_type[0]

        if not isinstance(as_type, type):
            return False

        if not issubclass(as_type, compare_to):
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

        return True


class Comparer:
    """
    Used to do matching, issubclass and isinstance between different objects.

    An instance of this is created and stored on :class:`strcs.TypeCache` objects.

    This object is used by the :class:`strcs.InstanceCheck` objects.
    """

    def __init__(self, type_cache: "TypeCache"):
        self.type_cache = type_cache

    def distill(self, classinfo: object, _chain: list[object] | None = None) -> tuple[object, bool]:
        from ._base import Type

        if _chain is None:
            _chain = []
        else:
            _chain = list(_chain)

        if classinfo in _chain:
            return classinfo, False

        optional: bool = False

        while (
            issubclass(classinfo_type := type(classinfo), (InstanceCheckMeta, Type))
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

        if classinfo is None:
            return type(None), True

        disassembled = self.type_cache.disassemble(classinfo)
        optional = optional or disassembled.optional
        _chain.append(classinfo)

        if disassembled.is_union:
            classinfo = disassembled.nonoptional_union_types
        elif disassembled.mro.all_vars:
            classinfo = disassembled.origin
        elif isinstance(classinfo, tuple) and type(None) in classinfo:
            classinfo = tuple(part for part in classinfo if part is not type(None))
            if len(classinfo) == 1:
                classinfo = classinfo[0]
        elif type(classinfo) in union_types:
            classinfo = tp.get_args(classinfo)

        result: object

        if isinstance(classinfo, tuple):
            found = tuple(self.distill(part, _chain=_chain) for part in classinfo)

            flat: list[object] = []

            def expand(got: object) -> None:
                if isinstance(got, tuple):
                    for part in got:
                        if part not in flat:
                            expand(part)
                else:
                    flat.append(got)

            expand(tuple(part for part, _ in found))
            if len(flat) == 1:
                result = flat[0]
            else:
                result = tuple(flat)
            is_valid = all(valid for _, valid in found)
        else:
            result, is_valid = self._distill_one(classinfo, _chain=_chain)

        if isinstance(result, tuple) and type(None) in result:
            optional = True

        if optional and result not in (None, type(None)):
            if not isinstance(result, tuple):
                result = (result, type(None))
            else:
                result = tuple(part for part in result if part is not type(None))
                result = tuple((*result, type(None)))

        return result, is_valid

    def _distill_one(
        self, classinfo: object, _chain: list[object] | None = None
    ) -> tuple[object, bool]:
        checkable = getattr(classinfo, "checkable", classinfo)
        Meta = getattr(checkable, "Meta", None)
        if Meta and (extracted := getattr(Meta, "extracted", None)) is not None:
            classinfo = extracted

        if not isinstance(classinfo, type):
            classinfo, is_valid = self.distill(classinfo, _chain=_chain)
        else:
            is_valid = True

        return classinfo, is_valid

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
        checking, checking_is_valid = self.distill(checking)
        check_against, check_against_is_valid = self.distill(check_against)

        if check_against_is_valid and (checking == () or not checking_is_valid):
            if subclasses:
                return isinstance(
                    checking,
                    check_against,  # type:ignore[arg-type]
                )
            else:
                if not isinstance(check_against, tuple):
                    check_against = (check_against,)
                return type(checking) in check_against

        if not checking_is_valid:
            return checking == check_against

        if isinstance(checking, tuple) and checking:
            if all(isinstance(part, type) for part in checking):
                checking = functools.reduce(operator.or_, checking)
            elif len(checking) == 2 and checking[1] in (None, type(None)):
                checking = tp.Optional[self.type_cache.disassemble(checking[0]).checkable]

        if (
            isinstance(check_against, tuple)
            and check_against
            and all(isinstance(part, type) for part in check_against)
        ):
            if all(isinstance(part, type) for part in check_against):
                check_against = functools.reduce(operator.or_, check_against)
            elif len(check_against) == 2 and check_against[1] in (None, type(None)):
                check_against = tp.Optional[self.type_cache.disassemble(check_against[0]).checkable]

        check_against = self.type_cache.disassemble(check_against)
        checking = self.type_cache.disassemble(checking)

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
                or (type(self.distill(matching_dis.fields_from)[0]) == matching_to_dis.fields_from)
            ):
                return False

        for mtv, mttv in zip(
            matching_dis.mro.all_vars,
            matching_to_dis.mro.all_vars,
        ):
            if isinstance(mtv, Type) and isinstance(mttv, Type):
                if not self.matches(mtv, mttv, subclasses=subclasses):
                    return False
            elif mtv is Type.Missing and not allow_missing_typevars:
                return False

        return True
