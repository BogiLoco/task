"""Base page object: explicit waits only (no time.sleep), every action logged ("ui")."""

from __future__ import annotations

import logging

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from framework import config

log = logging.getLogger("ui")


def describe(locator) -> str:
    """Locator for logs, e.g. ('id', 'x') -> '#x'."""
    by, value = locator
    return f"#{value}" if by == "id" else value


class BasePage:
    def __init__(self, driver: WebDriver):
        self.driver = driver
        self.wait = WebDriverWait(driver, config.DEFAULT_TIMEOUT)

    # -- actions -----------------------------------------------------------

    def open(self, url: str) -> None:
        # The user id in the URL is the only credential, so it is not logged.
        log.info("open %s", url.split("?")[0] + ("?user-id=…" if "user-id=" in url else ""))
        self.driver.get(url)

    def click(self, locator) -> None:
        log.info("click %s", describe(locator))
        self.wait.until(EC.element_to_be_clickable(locator)).click()

    def type_into(self, locator, text: str) -> None:
        log.info("type %r into %s", text, describe(locator))
        field = self.find_visible(locator)
        field.clear()
        field.send_keys(text)

    # -- waiting helpers ---------------------------------------------------

    def find(self, locator) -> WebElement:
        """Wait until the element is present and return it."""
        return self.wait.until(EC.presence_of_element_located(locator))

    def find_visible(self, locator) -> WebElement:
        return self.wait.until(EC.visibility_of_element_located(locator))

    def text_of(self, locator, *, quiet: bool = False) -> str:
        """Visible text; `quiet=True` skips the log (for polling loops)."""
        text = self.find_visible(locator).text.strip()
        if not quiet:
            log.info("read %s = %r", describe(locator), text)
        return text

    def wait_until_gone(self, locator) -> None:
        self.wait.until(EC.invisibility_of_element_located(locator))
