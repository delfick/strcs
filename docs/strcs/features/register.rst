.. _features_register:

The Register
------------

The register is a central object that holds knowledge of how to transform data
into different types. It is used to get a decorator that is used to add those
:ref:`creators <features_creators>` and also used to then do a conversion:

.. code-block:: python

    import strcs

    reg = strcs.CreateRegister()
    creator = reg.make_decorator()

    # Then the creator may be used as a decorator to add knowledge about custom
    # transformations

    # Then objects may be created
    instance = reg.create(MyKls, some_data)

Multiple registers
------------------

It is easy to have multiple registers as the creator functions can ask for the
current register with the special `_register: strcs.CreateRegister` in the
signature:

.. code-block:: python

    from attrs import define
    import strcs

    reg = strcs.CreateRegister()
    creator = reg.make_decorator()


    @define
    class MyKls:
        one: int


    @creator(MyKls)
    def create_mykls(val: tp.Any, /, _register: strcs.CreateRegister):
        assert _register is reg
        return True
    

    instance = reg.create(MyKls, {"one": 2})
    assert isinstance(instance, MyKls)
