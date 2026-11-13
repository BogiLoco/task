"""Header page object: the displayed balance."""

from __future__ import annotations

import contextlib

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from framework.pages.base_page import BasePage
from framework.utils.money import parse_eur


class Header(BasePage):
    BALANCE = (By.ID, "header-balance")

    def balance(self, *, quiet: bool = False) -> float:
        return parse_eur(self.text_of(self.BALANCE, quiet=quiet))

    def wait_for_balance(self, expected: float) -> float:
        """Wait up to 5 s for the balance to equal `expected`; return the last value seen."""
        with contextlib.suppress(TimeoutException):
            WebDriverWait(self.driver, 5).until(lambda _: self.balance(quiet=True) == expected)
        return self.balance()
