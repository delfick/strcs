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
    elif name == "strcs.CreateRegister":
        return "()", return_annotation
    elif name == "strcs.CreateRegister.create":
        return (
            "(typ: type[T] | strcs.Type[T], value: object = strcs.NotSpecified"
            ", meta: strcs.Meta | None = None"
            ", once_only_creator: strcs.ConvertFunction[T] | None = None)"
        ), return_annotation
    elif name == "strcs.CreateRegister.create_annotated":
        return (
            "(typ: type[T] | strcs.Type[T],"
            ", ann: MetaAnnotation | MergedMetaAnnotation | AdjustableMeta | AdjustableCreator | ConvertFunction[T]"
            ", value: object = strcs.NotSpecified"
            ", meta: strcs.Meta | None = None"
            ", once_only_creator: strcs.ConvertFunction[T] | None = None)"
        ), return_annotation
    elif name == "strcs.CreateRegister.make_decorator":
        return "()", "strcs.Creator"
    elif name == "strcs.MRO":
        return "", ""

    return None


def setup(app: Sphinx) -> SphinxExtMetadata:
    app.connect("autodoc-process-signature", process_signature)
    return {"parallel_read_safe": True}
