"""Success receipt modal page object.

Located by id, not `[role='dialog']`: the hidden filter popovers also use that role.
"""

from __future__ import annotations

from typing import Self

from selenium.webdriver.common.by import By

from framework.pages.base_page import BasePage
from framework.utils.money import parse_eur


class ReceiptModal(BasePage):
    MODAL = (By.ID, "modal-success")
    BET_ID = (By.ID, "modal-success-bet-id")
    MATCH = (By.ID, "modal-success-match")
    STAKE = (By.ID, "modal-success-stake")
    ODDS = (By.ID, "modal-success-odds")
    PAYOUT = (By.ID, "modal-success-payout")
    CLOSE = (By.ID, "modal-success-close")

    def wait_shown(self) -> Self:
        self.find_visible(self.MODAL)
        return self

    # -- field accessors ---------------------------------------------------

    def bet_id(self) -> str:
        return self.text_of(self.BET_ID)

    def match(self) -> str:
        return self.text_of(self.MATCH)

    def stake(self) -> float:
        return parse_eur(self.text_of(self.STAKE))

    def odds(self) -> float:
        return float(self.text_of(self.ODDS))

    def payout(self) -> float:
        return parse_eur(self.text_of(self.PAYOUT))

    # -- actions -----------------------------------------------------------

    def close(self) -> None:
        self.click(self.CLOSE)
        self.wait_until_gone(self.MODAL)
