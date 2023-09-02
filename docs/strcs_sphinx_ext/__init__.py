from sphinx.application import Sphinx
from sphinx_toolbox.utils import SphinxExtMetadata


def process_signature(
    app: Sphinx,
    what: str,
    name: str,
    obj: object,
    options: dict[str, object],
    signature: str | None,
    return_annotation: str | None,
) -> tuple[str, str | None] | None:
    if name == "strcs.AdjustableMeta.adjusted_meta":
        return "(meta: strcs.Meta, typ: strcs.Type[T], type_cache: strcs.TypeCache)", "strcs.Meta"
    if name == "strcs.AdjustableCreator.adjusted_creator":
        return (
            "(creator: strcs.ConvertFunction[T] | None, register: strcs.CreateRegister"
            ", typ: strcs.Type[T], type_cache: strcs.TypeCache)",
            "strcs.ConvertFunction[T] | None",
        )
    elif name == "strcs.Ann":
        return (
            "(meta: strcs.MetaAnnotation | strcs.MergedMetaAnnotation | strcs.AdjustableMeta[T] | None = None"
            ", creator: strcs.ConvertDefinition[T] | None = None)",
            return_annotation,
        )

    return None


def setup(app: Sphinx) -> SphinxExtMetadata:
    app.connect("autodoc-process-signature", process_signature)
    return {"parallel_read_safe": True}
