"""UI-only fixtures: the Chrome driver."""

from __future__ import annotations

import logging

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from framework import config as app_config

ui_log = logging.getLogger("ui")


@pytest.fixture
def driver():
    options = Options()
    if app_config.HEADLESS:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1400,1000")
    # Keep the browser console for the report (read at teardown).
    options.set_capability("goog:loggingPrefs", {"browser": "ALL"})
    drv = webdriver.Chrome(options=options)
    drv.implicitly_wait(0)  # explicit waits only
    ui_log.info(
        "Chrome %s started (headless=%s)",
        drv.capabilities.get("browserVersion", "?"),
        app_config.HEADLESS,
    )
    yield drv
    try:
        entries = drv.get_log("browser")
        ui_log.info("browser console: %d message(s)", len(entries))
        for entry in entries:
            ui_log.info("browser console [%s] %s", entry["level"], entry["message"])
    except Exception as exc:  # nice-to-have; never fail teardown
        ui_log.warning("could not read browser console: %s", exc)
    drv.quit()
