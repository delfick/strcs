from setuptools import setup

import runpy

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
      [ "cattrs==22.1.0"
      ]

    , extras_require =
      { 'tests' :
        [ "noseOfYeti==2.3.1"
        , "pytest==7.1.2"
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
