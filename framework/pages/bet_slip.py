"""Bet slip page object."""

from __future__ import annotations

from typing import Self

from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from framework.pages.base_page import BasePage, log


class BetSlip(BasePage):
    STAKE_INPUT = (By.ID, "bet-slip-stake-input")
    POTENTIAL_PAYOUT = (By.ID, "bet-slip-potential-payout")
    PLACE_BET = (By.ID, "bet-slip-place-bet")
    SELECTION_TEAMS = (By.CSS_SELECTOR, ".betSelectionTeams")

    def enter_stake(self, stake) -> Self:
        self.type_into(self.STAKE_INPUT, str(stake))
        return self

    def place_bet(self) -> Self:
        self.click(self.PLACE_BET)
        return self

    def is_enabled_while_placing(self) -> bool:
        """Whether Place Bet is still enabled during 'Placing...' (lasts ~0.5 s)."""
        WebDriverWait(self.driver, 3, poll_frequency=0.05).until(
            lambda d: "placing" in d.find_element(*self.PLACE_BET).text.lower()
        )
        button = self.driver.find_element(*self.PLACE_BET)
        enabled = button.is_enabled()
        log.info("Place Bet while placing: text=%r enabled=%s", button.text, enabled)
        return enabled

    def click_place_bet_again(self) -> Self:
        """Immediate second click: with `place_bet()` it forms a double click."""
        log.info("click #%s again (second click of a double click)", self.PLACE_BET[1])
        ActionChains(self.driver).click(self.driver.find_element(*self.PLACE_BET)).perform()
        return self

    def is_place_bet_enabled(self) -> bool:
        return self.find(self.PLACE_BET).is_enabled()

    def potential_payout_text(self) -> str:
        return self.text_of(self.POTENTIAL_PAYOUT)

    def selection_teams(self) -> str:
        return self.text_of(self.SELECTION_TEAMS)
