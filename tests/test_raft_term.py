# -*- coding: utf-8 -*-

import pytest

from canoe.term import RaftTerm

from .context import canoe


@pytest.fixture
def term():
    return RaftTerm()


def test_initialisation(term):
    assert term.current_term == 0
    assert term.voted_for is None
    assert term.votes == set()


def test_monotonicity(term):
    term.current_term += 1
    assert term.current_term == 1
    term.current_term = 2
    assert term.current_term == 2
    term.current_term += 0
    assert term.current_term == 2
    with pytest.raises(AttributeError) as error:
        term.current_term -= 1
        assert error.value.args[0] == "current_term must be monotonically increasing"
    with pytest.raises(AttributeError) as error:
        term.current_term = 1
        assert error.value.args[0] == "current_term must be monotonically increasing"
