"""
builtin_types: all the classes in the python global builtins
union_types: all the classes that are used by objects that represent typing Unions
"""

import builtins
import types
from typing import Union

builtin_types = [v for v in vars(builtins).values() if isinstance(v, type)]
union_types: list[object] = [type(Union[str, int]), type(str | int), types.UnionType, Union]
