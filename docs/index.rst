.. toctree::
   :hidden:

   strcs/changelog
   strcs/features/index
   strcs/features/register
   strcs/features/meta
   strcs/features/creators
   strcs/features/annotations

.. _strcs:

Structures (strcs)
==================

A Python3.10+ library that wraps `cattrs`_ for a modular
approach to constructing objects with the ability to string data through the process.

Install from pypi::

    > python -m pip install strcs


Why and What
------------

It's useful to be able to take one form of data and transform it into another.
For example taking some JSON data and using that as input for a class constructor.

The simplest way to do this is to create the constructor of the class such that
it takes in that data, however this couples that class to the specific shape of
that JSON. This is annoying when that same data may exist in different forms and
suddenly a transformation needs to take place before the class can be created.

Java solves this problem with multiple constructors, but in Python there can only
be one constructor. So another way to solve the problem is with class methods
that take in the different shapes of data and then plug that into the class
constructor.

This is great but then we have an inconsistent way of constructing the class for
any data shapes the class doesn't already know about.

A different approach is to say the class should only care about it's properties
and not be responsible for transforming different shapes of data into those
properties. This is the approach
`cattrs <https://cattrs.readthedocs.io/en/latest/readme.html>`_ takes
where it can do a reasonable amount of the heavy lifting involved in taking a
dictionary of data and transforming that into an instance of an
`attrs <https://www.attrs.org/en/stable/>`_ class.

This library is essentially a hook for a ``cattrs`` converter that provides a
slightly different take on how conversion logic may be expressed, whilst also
making it possible to provide a separate block of information that may be
accessed at any point in the conversion without being explicitly passed along.

Example
-------

Here is a contrived example that shows a couple features. Read the
:ref:`features` page for the full list of what is provided by ``strcs``:

.. code-block:: python

    from my_library import Renderer 

    from attrs import define
    import typing as tp
    import strcs


    # The register holds all of the creators
    # and the ``creator`` decorator used to add those creators
    reg = strcs.CreateRegister()
    creator = reg.make_decorator()


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
