import pytest

import strcs


@pytest.fixture()
def type_cache() -> strcs.TypeCache:
    return strcs.TypeCache()


@pytest.fixture()
def Dis(type_cache: strcs.TypeCache) -> strcs.disassemble.Disassembler:
    return type_cache.disassemble
