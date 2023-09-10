.. _features_register:

The Register
============

.. autoclass:: strcs.CreateRegister
    :members: make_decorator, create, create_annotated

Multiple registers
------------------

It is easy to have multiple registers as the creator functions can ask for the
current register with the special ``_register: strcs.CreateRegister`` in the
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
    def create_mykls(value: object, /, _register: strcs.CreateRegister) -> bool:
        assert _register is reg
        return True
    

    instance = reg.create(MyKls, {"one": 2})
    assert isinstance(instance, MyKls)

Resolving type annotations
--------------------------

.. automodule:: strcs.hints
