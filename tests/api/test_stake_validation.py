"""API test: stake validation on POST /api/place-bet.

Why chosen: a money-path rule that must hold in the API, not only in the UI
(Spec §4.1). Fast, deterministic, no browser, and it guards the worst bug (BUG-001).
Each rejected stake must also leave the balance unchanged.

Limits: €1.00 – €100.00, max 2 decimals. €1.00 per the API schema; the "€1.01" in
Spec §4.1 is a spec contradiction (see the bug report).
"""

import pytest
from pydantic import ValidationError

from framework.api.models import (
    ErrorResponse,
    PlaceBetResponse,
    PlaceBetResponseStrict,
    validate_response,
)

# (stake, accepted): accepted -> 200; rejected -> 422 and balance unchanged.
# TC-03 = min / max boundaries, TC-05 = format and precision.
STAKE_CASES = [
    pytest.param(0.99, False, id="below_min", marks=pytest.mark.testcase("TC-03.01")),
    pytest.param(1.00, True, id="at_min", marks=pytest.mark.testcase("TC-03.02")),
    pytest.param(1.01, True, id="just_above_min", marks=pytest.mark.testcase("TC-03.03")),
    pytest.param(100.00, True, id="at_max", marks=pytest.mark.testcase("TC-03.04")),
    pytest.param(100.01, False, id="above_max", marks=pytest.mark.testcase("TC-03.05")),
    pytest.param(10.555, False, id="three_decimals", marks=pytest.mark.testcase("TC-05.01")),
    pytest.param(0, False, id="zero", marks=pytest.mark.testcase("TC-05.02")),
]


@pytest.mark.api
@pytest.mark.parametrize(("stake", "accepted"), STAKE_CASES)
def test_stake_boundary_validation(api_client, reset_balance, upcoming_match, stake, accepted):
    balance_before = reset_balance

    resp = api_client.place_bet(upcoming_match.id, "HOME", stake)

    if accepted:
        assert resp.status_code == 200, (
            f"stake {stake} should be accepted, got {resp.status_code}: {resp.text}"
        )
        model = validate_response(PlaceBetResponse, resp.json())
        assert model.stake == stake
        # Odds are static for the session (Spec §3).
        assert model.odds == upcoming_match.odds.home
    else:
        assert resp.status_code == 422, (
            f"stake {stake} should be rejected with 422, got {resp.status_code}: {resp.text}"
        )
        validate_response(ErrorResponse, resp.json())
        balance_after = api_client.balance_value()
        assert balance_after == balance_before, (
            f"balance must not change for a rejected stake "
            f"(before={balance_before}, after={balance_after})"
        )


@pytest.mark.api
@pytest.mark.testcase("TC-05.03")
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="BUG-001: API accepts negative stake (200) and increases the balance "
    "instead of rejecting with 422.",
)
def test_negative_stake_is_rejected(api_client, reset_balance, upcoming_match):
    """A negative stake is rejected and never increases the balance (Spec §4.1)."""
    balance_before = reset_balance

    resp = api_client.place_bet(upcoming_match.id, "HOME", -50)

    assert resp.status_code == 422, f"expected 422, got {resp.status_code}: {resp.text}"
    assert api_client.balance_value() <= balance_before, "negative stake increased balance"


@pytest.mark.api
@pytest.mark.testcase("TC-06.01")
@pytest.mark.xfail(
    strict=True,
    raises=ValidationError,
    reason="BUG-008: place-bet returns currency 'USD' not 'EUR'; BUG-009: payout is "
    "0.01 short of stake×odds for some stakes (1 × 4.10 → 4.09). "
    "Full contract fails until both are fixed.",
)
def test_place_bet_response_matches_full_contract(api_client, reset_balance, upcoming_match):
    """A bet response meets the full contract (currency EUR, payout = stake × odds)."""
    resp = api_client.place_bet(upcoming_match.id, "HOME", 10)
    assert resp.status_code == 200, f"expected 200, got {resp.status_code}: {resp.text}"

    validate_response(PlaceBetResponseStrict, resp.json())
