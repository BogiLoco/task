"""Money helpers shared by the UI and API layers."""

from __future__ import annotations

import re
from decimal import ROUND_HALF_UP, Decimal

_EUR_RE = re.compile(r"€\s*(-?[0-9]+(?:\.[0-9]{1,2})?)")


def parse_eur(text: str) -> float:
    """Extract the first euro amount from a UI string, e.g. '€24.50' -> 24.5."""
    match = _EUR_RE.search(text)
    if not match:
        raise ValueError(f"no euro amount found in {text!r}")
    return float(match.group(1))


def expected_payout(stake: float, odds: float) -> float:
    """stake × odds, rounded half-up to the cent.

    Decimal, not float: `round(1.70 * 1.35, 2)` gives 2.29 instead of 2.30 (cf. BUG-009).
    """
    exact = Decimal(str(stake)) * Decimal(str(odds))
    return float(exact.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
