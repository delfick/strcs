.. _changelog:

Changelog
---------

.. _release-0.4.0:

0.4.0 - 15 October 2023
    * Add a ``disassemble`` method to the type cache and implemented ``disassemble``
      on ``strcs.Type`` using it. Note that the signature also changes to no
      longer have an "expect" but also it's smarter about the resulting Type
      it returns.
    * Made ``strcs.Type`` and related functionality all understand
      ``typing.NewType`` objects.

.. _release-0.3.0:

0.3.0 - 17 September 2023
    * Introduced a number of helpers for introspecting type annotations
    * Introduced new ``strcs.Type`` class for representing types and creators
      now take these objects.
    * Can now create and use creators for generics so that when using the register
      to create an object, the filled type vars of the provided type are
      understood and respected.
    * Updated dependencies
    * Converted packaging to hatchling

.. _release-0.2.0:

0.2.0 - 30 October 2022
    * Renamed toggle for auto resolution of string annotations
    * Fixed structuring object as a type

.. _release-0.1.3:

0.1.3 - 29 October 2022
    * Improved error messages from creators failing

.. _release-0.1.2:

0.1.2 - 29 October 2022
    * Added py.typed file to the distribution
    * Removed need for the recursed option
    * Added resolution of string type annotations on attrs/dataclass/normal
      classes

.. _release-0.1.1:

0.1.1 - 26 September 2022
    * Fix a bunch of typing problems

.. _release-0.1.0:

0.1.0 - 21 August 2022
    * Initial release
    * Note this code is not actively used by anything yet
