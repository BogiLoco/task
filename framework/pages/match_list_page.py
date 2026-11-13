"""Match list page object."""

from __future__ import annotations

from typing import Self

from selenium.webdriver.common.by import By

from framework import config
from framework.pages.base_page import BasePage, log

SELECTIONS = ("home", "draw", "away")


class MatchListPage(BasePage):
    MATCH_LIST = (By.ID, "match-list")

    def load(self) -> Self:
        self.open(config.app_url())
        self.find(self.MATCH_LIST)  # wait for the list to render
        return self

    # -- locators scoped to a match ----------------------------------------

    @staticmethod
    def odds_button(match_id: str, selection: str):
        assert selection in SELECTIONS, f"selection must be one of {SELECTIONS}"
        return (By.ID, f"odds-{match_id}-{selection}")

    # -- actions / queries -------------------------------------------------

    def odds_value(self, match_id: str, selection: str) -> float:
        """Odds shown on an outcome button."""
        btn = self.find(self.odds_button(match_id, selection))
        value = btn.find_element(By.CSS_SELECTOR, ".oddsButtonValue").text.strip()
        return float(value)

    def select_outcome(self, match_id: str, selection: str) -> float:
        """Click an outcome and return the odds it showed."""
        odds = self.odds_value(match_id, selection)
        log.info("select %s on %s (odds %.2f)", selection.upper(), match_id, odds)
        self.click(self.odds_button(match_id, selection))
        return odds
