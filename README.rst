Structures
==========

A Python3.10+ library that wraps `cattrs <https://cattrs.readthedocs.io>`_ for a
modular approach to constructing objects with the ability to string data through
the process.

Install from pypi::

    > python -m pip install strcs

Documentation at https://strcs.readthedocs.io/

Development
-----------

To run tests, install the code in a virtualenv and use the provided helper::

    > mkdir -p ~/.virtualenvs
    > python -m venv ~/.virtualenvs/strcs
    > source ~/.virtualenvs/strcs
    > python -m pip install -e ".[tests]"
    > ./test.sh
