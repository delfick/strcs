# coding: spec

import strcs

import pytest

describe "NotSpecified":
    it "cannot be instantiated":
        with pytest.raises(Exception, match="Do not instantiate NotSpecified"):
            strcs.NotSpecified()

    it "has a reasonable repr":
        assert repr(strcs.NotSpecified) == "<NotSpecified>"
