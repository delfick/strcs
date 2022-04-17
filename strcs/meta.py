import typing as tp

T = tp.TypeVar("T")
U = tp.TypeVar("U")


def extract_type(typ: T) -> tp.Tuple[bool, U]:
    """
    Given some type, return a tuple of (optional, type)

    So str would return (False, str)

    whereas tp.Optional[str] would return (True, str)

    and str | bool would return (False, str | bool)

    but tp.Optional[str | bool] would return (True, str | bool)
    """
    optional = False
    if tp.get_origin(typ) is tp.Union:
        args = tp.get_args(typ)
        if len(args) > 1 and isinstance(args[-1], type) and issubclass(args[-1], type(None)):
            if len(args) == 2:
                typ = args[0]
            else:
                # A tp.Optional[tp.Union[arg1, arg2]] is equivalent to tp.Union[arg1, arg2, None]
                # So we must create a copy of the union with just arg1 | arg2
                # We tell mypy to be quiet with the noqa because I can't make it understand typ is a Union
                typ = typ.copy_with(args[:-1])  # type: ignore
            optional = True

    return optional, tp.cast(U, typ)
