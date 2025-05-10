import pytest

import strcs


class TestNotSpecified:
    def test_it_cannot_be_instantiated(self):
        with pytest.raises(Exception, match="Do not instantiate NotSpecified"):
            strcs.NotSpecified()

    def test_it_has_a_reasonable_repr(self):
        assert repr(strcs.NotSpecified) == "<NotSpecified>"
