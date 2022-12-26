# coding: spec

import typing as tp

from attrs import define

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
def create_images(value: object, /, excluded: list[str] | None) -> dict | None:
    if isinstance(value, dict):
        if excluded is None:
            excluded = []

        found = []
        for author, filenames in value.items():
            if author not in excluded and isinstance(filenames, list):
                for filename in filenames:
                    found.append({"author": author, "filename": filename})

        return {"images": found}

    return None


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
