"""Thin client for the Sports Betting API.

Returns raw responses and does not raise on 4xx/5xx: negative tests need them.
Every request and response is logged (logger "api") for the HTML report.
"""

from __future__ import annotations

import logging
import time
from datetime import date

import requests

from framework import config
from framework.api.models import BalanceResponse, Match

REQUEST_TIMEOUT = 15  # seconds; a hung server fails the test, not the whole run
LOG_BODY_LIMIT = 1500

log = logging.getLogger("api")


def _mask(user_id: str) -> str:
    """The user id is the only credential, so logs show only its start."""
    return user_id[:12] + "…" if len(user_id) > 12 else "…"


def _clip(text: str) -> str:
    return text if len(text) <= LOG_BODY_LIMIT else f"{text[:LOG_BODY_LIMIT]}… [{len(text)} chars]"


class BettingClient:
    def __init__(self):
        self.base_url = config.BASE_URL
        self._session = requests.Session()
        self._session.headers.update({"x-user-id": config.USER_ID})

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        timeout = kwargs.pop("timeout", REQUEST_TIMEOUT)
        # Prepared first, so the exact request is logged before it is sent.
        prepared = self._session.prepare_request(
            requests.Request(method, f"{self.base_url}{path}", **kwargs)
        )
        self._log_request(prepared)
        started = time.perf_counter()
        try:
            resp = self._session.send(prepared, timeout=timeout)
        except requests.RequestException as exc:
            log.error(
                "✘ %s %s failed after %.0f ms: %s",
                method,
                path,
                (time.perf_counter() - started) * 1000,
                exc,
            )
            raise
        log.info(
            "← %s %s (%.0f ms)\n   body:    %s",
            resp.status_code,
            resp.reason,
            (time.perf_counter() - started) * 1000,
            _clip(resp.text) or "—",
        )
        return resp

    @staticmethod
    def _log_request(req: requests.PreparedRequest) -> None:
        body = req.body.decode() if isinstance(req.body, bytes) else req.body
        headers = {
            k: v for k, v in req.headers.items() if k.lower() in ("x-user-id", "content-type")
        }
        if "x-user-id" in headers:
            headers["x-user-id"] = _mask(headers["x-user-id"])
        log.info(
            "→ %s %s\n   headers: %s\n   body:    %s",
            req.method,
            req.path_url,
            headers,
            body or "—",
        )

    # -- reads -------------------------------------------------------------

    def get_matches(self) -> requests.Response:
        return self._request("GET", "/api/matches")

    def get_balance(self) -> requests.Response:
        return self._request("GET", "/api/balance")

    # -- writes ------------------------------------------------------------

    def place_bet(self, match_id: str, selection: str, stake) -> requests.Response:
        # `stake` is untyped on purpose: negative tests send invalid values.
        body = {"matchId": match_id, "selection": selection, "stake": stake}
        return self._request("POST", "/api/place-bet", json=body)

    def reset_balance(self) -> requests.Response:
        return self._request("POST", "/api/reset-balance")

    # -- convenience -------------------------------------------------------

    def balance_value(self) -> float:
        """Persisted balance; every read also validates the GET /api/balance contract."""
        resp = self.get_balance()
        assert resp.status_code == 200, f"GET /api/balance failed: {resp.status_code} {resp.text}"
        return BalanceResponse.model_validate(resp.json()).balance

    def upcoming_matches(self) -> list[Match]:
        """Matches with a kickoff date after today, soonest first."""
        resp = self.get_matches()
        assert resp.status_code == 200, f"GET /api/matches failed: {resp.status_code} {resp.text}"
        today = date.today()
        matches = [Match.model_validate(m) for m in resp.json()]
        return sorted((m for m in matches if m.kickoffDate > today), key=lambda m: m.kickoffDate)
