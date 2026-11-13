"""Pydantic models of the API contract (Spec §5.3): fields, types and business rules."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any, Self, TypeVar

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator, model_validator

from framework.utils.money import expected_payout

log = logging.getLogger("contract")

ModelT = TypeVar("ModelT", bound=BaseModel)


def validate_response(model: type[ModelT], data: Any) -> ModelT:
    """Parse `data` into `model`; log ✔ or ✘ with each failing field, then re-raise."""
    try:
        parsed = model.model_validate(data)
    except ValidationError as exc:
        problems = "\n".join(
            f"   - {'.'.join(map(str, e['loc'])) or '(root)'}: {e['msg']}"
            + ("" if e["type"] == "value_error" else f" (got {e.get('input')!r})")
            for e in exc.errors()
        )
        log.error("✘ %s: response does not match the contract\n%s", model.__name__, problems)
        raise
    log.info("✔ %s: response matches the contract", model.__name__)
    return parsed


class Odds(BaseModel):
    home: float
    draw: float
    away: float


class Match(BaseModel):
    """One entry of GET /api/matches."""

    id: str
    competition: str
    kickoffDate: date
    homeTeam: str
    awayTeam: str
    odds: Odds


class BalanceResponse(BaseModel):
    """GET /api/balance."""

    # Unknown fields fail: catches contract drift (an extra or renamed field).
    model_config = ConfigDict(extra="forbid")

    balance: float
    currency: str

    @field_validator("currency")
    @classmethod
    def currency_must_be_eur(cls, v: str) -> str:
        if v != "EUR":
            raise ValueError(f"currency must be 'EUR', got {v!r}")
        return v


class PlaceBetResponse(BaseModel):
    """200 response of POST /api/place-bet: fields and types only.

    Business rules the live app breaks are in `PlaceBetResponseStrict`.
    """

    # An added response field should not break the shape check.
    model_config = ConfigDict(extra="allow")

    message: str
    matchId: str
    selection: str
    stake: float
    odds: float
    payout: float
    balance: float
    currency: str

    @field_validator("selection")
    @classmethod
    def selection_in_enum(cls, v: str) -> str:
        if v not in ("HOME", "DRAW", "AWAY"):
            raise ValueError(f"selection must be HOME/DRAW/AWAY, got {v!r}")
        return v


class PlaceBetResponseStrict(PlaceBetResponse):
    """Full contract: also currency == EUR (BUG-008) and payout == stake × odds (BUG-009)."""

    @field_validator("currency")
    @classmethod
    def currency_must_be_eur(cls, v: str) -> str:
        if v != "EUR":
            raise ValueError(f"currency must be 'EUR', got {v!r}")
        return v

    @model_validator(mode="after")
    def payout_matches_stake_times_odds(self) -> Self:
        expected = expected_payout(self.stake, self.odds)
        if self.payout != expected:
            raise ValueError(
                f"payout {self.payout} != stake×odds {expected} ({self.stake} × {self.odds})"
            )
        return self


class ErrorResponse(BaseModel):
    """Error body of 4xx/5xx responses."""

    model_config = ConfigDict(extra="allow")

    error: str
    message: str | None = None
