"""E2E UI test: place a single bet (TC-01).

Why chosen: the core user journey and main revenue path, covering selection, stake,
payout, the 'Placing...' state, the receipt and the balance deduction in one flow.
Known bugs are xfail(strict) checks on the same journey; each turns red once fixed.
"""

import contextlib

import pytest
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait

from framework.pages.bet_slip import BetSlip
from framework.pages.header import Header
from framework.pages.match_list_page import MatchListPage
from framework.pages.receipt_modal import ReceiptModal
from framework.utils.money import expected_payout, parse_eur

STAKE = 10.00
# A stake with cents, so a wrong payout factor shows up.
ODD_STAKE = 1.01


@pytest.mark.ui
@pytest.mark.testcase("TC-01.01")
def test_place_bet_shows_receipt(driver, reset_balance, upcoming_match):
    """Select an outcome, place a €10 bet, and confirm the receipt shows the bet."""
    matches = MatchListPage(driver).load()

    odds = matches.select_outcome(upcoming_match.id, "home")
    assert odds == upcoming_match.odds.home, "odds button should show the catalogue odds"

    slip = BetSlip(driver)
    assert upcoming_match.homeTeam in slip.selection_teams()

    slip.enter_stake(STAKE)
    assert slip.is_place_bet_enabled(), "Place Bet should enable once a valid stake is entered"

    slip.place_bet()

    receipt = ReceiptModal(driver).wait_shown()
    assert receipt.bet_id(), "receipt should show a bet id"
    assert upcoming_match.homeTeam in receipt.match(), "receipt should show the match"
    assert receipt.stake() == STAKE, "receipt should show the €10.00 stake"
    assert receipt.odds() == odds, "receipt should show the odds at placement"


@pytest.mark.ui
@pytest.mark.testcase("TC-01.02")
def test_place_bet_deducts_stake(driver, api_client, reset_balance, upcoming_match):
    """A €10 UI bet lowers the persisted balance (GET /api/balance) by exactly €10."""
    balance_before = reset_balance

    MatchListPage(driver).load().select_outcome(upcoming_match.id, "home")
    BetSlip(driver).enter_stake(STAKE).place_bet()
    ReceiptModal(driver).wait_shown()

    balance_after = api_client.balance_value()
    assert round(balance_before - balance_after, 2) == STAKE, (
        f"balance should drop by exactly €{STAKE} (before={balance_before}, after={balance_after})"
    )


@pytest.mark.ui
@pytest.mark.testcase("TC-01.03")
@pytest.mark.xfail(
    strict=True,
    # Only an assertion is the known bug; a locator timeout is a real FAIL.
    raises=AssertionError,
    reason="BUG-006: receipt payout is stake × 2 instead of stake × odds "
    "(e.g. €1.01 × 2.45: slip €2.47, receipt €2.02); BUG-010: receipt lists the away team first.",
)
def test_receipt_matches_bet_slip(driver, reset_balance, upcoming_match):
    """The receipt shows the payout and team order the bet slip showed (Domain Context)."""
    odds = MatchListPage(driver).load().select_outcome(upcoming_match.id, "home")
    slip = BetSlip(driver).enter_stake(ODD_STAKE)

    slip_payout = parse_eur(slip.potential_payout_text())
    # Precondition: pytest.fail is not an AssertionError, so it is a real FAIL, not xfail.
    if slip_payout != expected_payout(ODD_STAKE, odds):
        pytest.fail(f"bet slip payout €{slip_payout} != stake × odds ({ODD_STAKE} × {odds})")

    slip.place_bet()
    receipt = ReceiptModal(driver).wait_shown()

    assert receipt.payout() == slip_payout, (
        f"receipt payout €{receipt.payout()} should equal the €{slip_payout} quoted in the bet slip"
    )
    expected_match = f"{upcoming_match.homeTeam} vs {upcoming_match.awayTeam}"
    assert receipt.match() == expected_match, (
        f"receipt should show {expected_match!r} (home first), got {receipt.match()!r}"
    )


@pytest.mark.ui
@pytest.mark.testcase("TC-01.04")
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="BUG-003: the displayed balance is not updated after a bet until the page "
    "is reloaded (the persisted balance is).",
)
def test_displayed_balance_updates_after_bet(driver, reset_balance, upcoming_match):
    """The displayed balance drops by the stake after a bet (Spec §2.2, §2.3)."""
    header = Header(driver)
    MatchListPage(driver).load()
    if header.balance() != reset_balance:
        pytest.fail(f"precondition: header shows €{header.balance()}, API €{reset_balance}")

    MatchListPage(driver).select_outcome(upcoming_match.id, "home")
    BetSlip(driver).enter_stake(STAKE).place_bet()
    ReceiptModal(driver).wait_shown().close()

    expected = round(reset_balance - STAKE, 2)
    shown = header.wait_for_balance(expected)
    assert shown == expected, (
        f"header should show €{expected} after a €{STAKE} bet, still shows €{shown}"
    )


@pytest.mark.ui
@pytest.mark.testcase("TC-01.05")
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="BUG-004: Place Bet stays enabled while 'Placing...', so a double click "
    "places the bet twice and charges the stake twice; only one receipt is shown.",
)
def test_double_click_places_one_bet(driver, api_client, reset_balance, upcoming_match):
    """A double click places one bet and charges the stake once (Spec §2.3).

    The charge depends on server timing (sometimes 409), so the button state during
    'Placing...' is checked too: it is deterministic and keeps the xfail stable.
    """
    MatchListPage(driver).load().select_outcome(upcoming_match.id, "home")
    slip = BetSlip(driver).enter_stake(STAKE).place_bet()
    enabled_while_placing = slip.is_enabled_while_placing()
    if enabled_while_placing:
        slip.click_place_bet_again()
    ReceiptModal(driver).wait_shown()

    # A second request may still be in flight: watch the balance for up to 5 s.
    single_charge = round(reset_balance - STAKE, 2)
    with contextlib.suppress(TimeoutException):
        WebDriverWait(driver, timeout=5, poll_frequency=0.5).until(
            lambda _: api_client.balance_value() < single_charge
        )
    balance_after = api_client.balance_value()
    charged = round(reset_balance - balance_after, 2)

    assert charged == STAKE, (
        f"one bet of €{STAKE} expected, but €{charged} was charged "
        f"(balance {reset_balance} -> {balance_after})"
    )
    assert not enabled_while_placing, (
        "Place Bet must not accept a second click while 'Placing...' (it is still enabled)"
    )
