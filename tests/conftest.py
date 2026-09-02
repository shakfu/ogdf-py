"""Fixtures shared by the test suite.

OGDF draws all randomness from one process-wide engine, so an unseeded
generator call returns whatever position that engine happens to be in - which
depends on what ran before it. Seeding before every test makes each test
independent of the order it runs in and of which subset was selected.
"""

import pytest

import ogdf

# Arbitrary fixed value; only its constancy matters.
SEED = 20260902


@pytest.fixture(autouse=True)
def seeded_engine():
    """Put OGDF's engine in the same state before every test."""
    ogdf.set_seed(SEED)
