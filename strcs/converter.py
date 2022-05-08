from cattr import GenConverter
import typing as tp

converter = GenConverter(prefer_attrib_converters=True)


def convert_union_str_list_str(o: tp.Any, _: tp.Any) -> tp.Union[str, list[str]]:
    if isinstance(o, str):
        return converter.structure(o, str)
    elif isinstance(o, list):
        return converter.structure(o, list)
    else:
        raise Exception(f"Unknown type: {type(o)}")


converter.register_structure_hook(tp.Union[str, list[str]], convert_union_str_list_str)
