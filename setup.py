import runpy

from setuptools import setup

VERSION = runpy.run_path("strcs/version.py")["VERSION"]

# fmt: off

# Setup the project
setup(
      name = "strcs"
    , version = VERSION
    , packages = ['strcs']
    , package_data =
      { "strcs": ["py.typed"]
      }

    , python_requires = ">= 3.10"

    , install_requires =
      [ "attrs==22.2.0"
      , "cattrs==22.2.0"
      ]

    , extras_require =
      { 'tests' :
        [ "noseOfYeti[black]==2.4.2"
        , "pytest==7.2.0"
        ]
      }

    # metadata
    , url = "http://github.com/delfick/strcs"
    , author = "Stephen Moore"
    , author_email = "stephen@delfick.com"
    , description = "Wrapper to make it more convenient to make structure hooks for cattrs"
    , long_description = open("README.rst").read()
    , license = "MIT"
    )

# fmt: on
