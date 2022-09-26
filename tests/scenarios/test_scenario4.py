# coding: spec

from attrs import define
import typing as tp
import strcs


class Renderer:
    pass


reg = strcs.CreateRegister()
creator = reg.make_decorator()


@define
class Image:
    author: str
    filename: str
    renderer: tp.Annotated[Renderer, strcs.FromMeta("renderer")]


@define
class Images:
    images: list[Image]


@creator(Images)
def create_images(
    val: dict[str, list[str]], /, excluded: tp.Optional[list[str]]
) -> strcs.ConvertResponse[Images]:
    if isinstance(val, dict):
        if excluded is None:
            excluded = []

        found = []
        for author, filenames in val.items():
            if author not in excluded and isinstance(filenames, list):
                for filename in filenames:
                    found.append({"author": author, "filename": filename})

        return {"images": found}


describe "example in the readme":

    it "works":
        renderer = Renderer()
        configuration = {
            "stephen": ["one.png", "two.png"],
            "joe": ["three.png", "four.png"],
            "bill": ["five.png", "six.png"],
        }
        meta = strcs.Meta({"renderer": renderer})

        images = reg.create(Images, configuration, meta=meta)
        assert isinstance(images, Images)
        assert set([i.author for i in images.images]) == set(["stephen", "joe", "bill"])
        assert all(i.renderer is renderer for i in images.images)

        images = reg.create(Images, configuration, meta=meta.clone({"excluded": ["stephen"]}))
        assert isinstance(images, Images)
        assert set([i.author for i in images.images]) == set(["joe", "bill"])
        assert all(i.renderer is renderer for i in images.images)
