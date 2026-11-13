"""Fixtures shared by API and UI tests.

All tests use one user id, so the suite must run serially (per-user 409 lock).
"""

from __future__ import annotations

import pytest

from framework.api.betting_client import BettingClient
from framework.api.models import Match

# -- API client and test data (UI tests use them for setup too) -------------------


@pytest.fixture
def api_client() -> BettingClient:
    return BettingClient()


@pytest.fixture(scope="session")
def upcoming_match() -> Match:
    """Soonest upcoming match; picked at run time so it never becomes a PAST match."""
    matches = BettingClient().upcoming_matches()
    if not matches:
        pytest.fail("No upcoming match in the catalogue; cannot run bet placement tests.")
    return matches[0]


@pytest.fixture
def reset_balance(api_client: BettingClient):
    """Reset the balance and return it as read by GET (the reset response is wrong, BUG-007)."""
    api_client.reset_balance()
    return api_client.balance_value()
