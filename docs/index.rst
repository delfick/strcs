.. toctree::
   :hidden:

   strcs/features
   strcs/changelog

.. _strcs:

Structures
==========

Some code that wraps cattrs/attrs for a modular approach to constructing objects
with the ability to string data through the process.

Install from pypi::

    > python -m pip install strcs

Example
-------

This library works by registering ``creators`` that know how to create
particular objects. You then use that register to convert from one type of data
into another. It is very similar to how ``cattrs`` works and being built on top
of it is a superset of cattrs features.

Here is a contrived example that shows a couple features. Read the
:ref:`features` page for the full list of what is provided by strcs:

.. code-block:: python

    from my_library import Renderer 

    from functools import partial
    from attrs import define
    import typing as tp
    import strcs


    # The register holds all of our creators
    # and the ``creator`` decorator we make is used to register those creators
    reg = strcs.CreateRegister()
    creator = partial(strcs.CreatorDecorator, reg)


    @define
    class Image:
        author: str
        filename: str

        # Here we're using dependency injection to say get ``renderer`` from
        # the meta object we provide when creating objects.
        renderer: tp.Annotated[Renderer, strcs.FromMeta("renderer")]


    @define
    class Images:
        images: list[Image]


    @creator(Images)
    def create_images(
        val: dict[str, list[str]], /, excluded: tp.Optional[list[str]]
    ) -> strcs.ConvertResponse:
        """
        Please note that type annotations are not runtime constraints in python
        and there is no guarantee that what is passed in is a dictionary of str
        to list of strings. And so you must still do those checks in the body of
        the creator. Returning None from this function is the same as saying the
        input was unexpected.

        You return a value that is then used to generate the desired object.
        Creators can also be generator functions so you may do something with
        the object that was created.

        Here we have also taken the ``excluded`` list from meta (found on type
        and name) and use that to exclude some results from what we use to make
        our Images object.
        """
        if isinstance(val, dict):
            if excluded is None:
                excluded = []

            found = []
            for author, filenames in val.items():
                if author not in excluded and isinstance(filenames, list):
                    for filename in filenames:
                        found.append({"author": author, "filename": filename})

            return {"images": found}


    renderer = Renderer()
    configuration = {
        "stephen": ["one.png", "two.png"],
        "joe": ["three.png", "four.png"],
        "bill": ["five.png", "six.png"],
    }

    # The meta object may also be given a custom cattrs Converter. In this case
    # we do not and a blank one is made for us.
    meta = strcs.Meta({"renderer": renderer})

    # First pass has no excluded authors
    images = reg.create(Images, configuration, meta=meta)
    assert isinstance(images, Images)
    assert set([i.author for i in images.images]) == set(["stephen", "joe", "bill"])
    assert all(i.renderer is renderer for i in images.images)

    # whereas this result doesn't have the stephen author
    # in both cases we turn a dictionary keyed by author into a flat list
    # And each item in that list is already loaded with our ``renderer`` object.
    images = reg.create(Images, configuration, meta=meta.clone({"excluded": ["stephen"]}))
    assert isinstance(images, Images)
    assert set([i.author for i in images.images]) == set(["joe", "bill"])
    assert all(i.renderer is renderer for i in images.images)
