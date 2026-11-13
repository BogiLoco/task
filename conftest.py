"""Run-wide hooks: per-run report folder, test case ids, screenshots.

Fixtures live in tests/conftest.py (shared) and tests/ui/conftest.py (UI only).
"""

from __future__ import annotations

import base64
import logging
import re
from datetime import datetime
from pathlib import Path

import pytest

from framework import config as app_config

REPORTS_DIR = Path(__file__).resolve().parent / "reports"

ui_log = logging.getLogger("ui")


# -- per-run report folder -------------------------------------------------------


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    """Write report.html and junit.xml to reports/<timestamp>/ unless a path is given.

    tryfirst: must run before pytest-html and junitxml read their paths.
    """
    if not hasattr(config.option, "htmlpath"):  # pytest-html not installed
        return
    if not config.option.htmlpath:
        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        config.option.htmlpath = str(REPORTS_DIR / stamp / "report.html")
    run_dir = Path(config.option.htmlpath).resolve().parent
    if not config.option.xmlpath:
        config.option.xmlpath = str(run_dir / "junit.xml")


@pytest.hookimpl(optionalhook=True)
def pytest_metadata(metadata):
    """Environment table at the top of the HTML report."""
    metadata["Base URL"] = app_config.BASE_URL
    metadata["Headless"] = str(app_config.HEADLESS)


# -- test case ids (docs/01_test_plan.md) ----------------------------------------

TEST_PLAN_IDS = {f"TC-{n:02d}" for n in range(1, 7)}
TESTCASE_ID = re.compile(r"^(TC-\d{2})\.(\d{2})$")


def testcase_id(item: pytest.Item) -> str | None:
    marker = item.get_closest_marker("testcase")
    return marker.args[0] if marker and marker.args else None


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(config, items):
    """Require a unique `TC-xx.yy` id per test and make it selectable with `-k`.

    tryfirst: the keyword must exist before pytest applies `-k`.
    """
    problems = []
    seen: dict[str, str] = {}
    for item in items:
        tc = testcase_id(item)
        match = TESTCASE_ID.match(tc or "")
        if tc is None:
            problems.append(f'{item.nodeid}: missing @pytest.mark.testcase("TC-xx.yy")')
        elif not match:
            problems.append(f"{item.nodeid}: {tc!r} is not in the form TC-xx.yy")
        elif match.group(1) not in TEST_PLAN_IDS:
            problems.append(f"{item.nodeid}: {match.group(1)!r} is not a scenario in the plan")
        elif tc in seen:
            problems.append(f"{item.nodeid}: {tc!r} is already used by {seen[tc]}")
        else:
            seen[tc] = item.nodeid
            item.extra_keyword_matches.add(tc)
            item.user_properties.append(("testcase", tc))
            item.user_properties.append(("scenario", match.group(1)))
    if problems:
        raise pytest.UsageError("Test case ids:\n  " + "\n  ".join(problems))


# -- reporting ---------------------------------------------------------------


@pytest.hookimpl(hookwrapper=True)
def pytest_report_teststatus(report, config):
    """Terminal status with the id, e.g. `PASSED [TC-03.02]`."""
    outcome = yield
    tc = getattr(report, "testcase", "")
    category, letter, word = outcome.get_result()
    if not tc or not word:
        return
    word = (f"{word[0]} [{tc}]", word[1]) if isinstance(word, tuple) else f"{word} [{tc}]"
    outcome.force_result((category, letter, word))


def pytest_html_report_title(report):
    report.title = "Sports Betting QA — test report"


@pytest.hookimpl(optionalhook=True)
def pytest_html_results_table_header(cells):
    cells.insert(1, '<th class="sortable" data-column-type="testcase">Test case</th>')


@pytest.hookimpl(optionalhook=True)
def pytest_html_results_table_row(report, cells):
    cells.insert(1, f"<td>{getattr(report, 'testcase', '')}</td>")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Add the test case id to the report; screenshot failed and xfailed UI tests.

    xfailed tests too: the screenshot shows the known bug.
    """
    outcome = yield
    report = outcome.get_result()
    report.testcase = testcase_id(item) or ""

    drv = item.funcargs.get("driver")
    if report.when != "call" or drv is None:
        return
    if not (report.failed or hasattr(report, "wasxfail")):
        return

    screenshot_dir = _run_dir(item.config) / "screenshots"
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    safe = item.name.replace("/", "_").replace("[", "_").replace("]", "_")
    status = "XFAIL" if hasattr(report, "wasxfail") else "FAILED"
    try:
        png = drv.get_screenshot_as_png()
    except Exception as exc:  # never mask the real failure
        ui_log.warning("screenshot failed: %s", exc)
        return
    (screenshot_dir / f"{status}_{safe}.png").write_bytes(png)

    html = item.config.pluginmanager.getplugin("html")
    if html is not None:
        extras = getattr(report, "extras", [])
        extras.append(html.extras.png(base64.b64encode(png).decode("ascii"), name=status))
        report.extras = extras


def _run_dir(config: pytest.Config) -> Path:
    """Folder of the current run (next to report.html)."""
    html_path = getattr(config.option, "htmlpath", None)
    return Path(html_path).resolve().parent if html_path else REPORTS_DIR
