# Sports Betting QA — Automation Framework

A small, focused test automation project for the Single Bet Placement feature of
the Sports Betting QA Assessment App. It implements two high-value automated
tests — one end-to-end UI journey and one API business-rule check — on top of a
clean, reusable framework.

## Deliverables

| Part | Document | What is in it |
|---|---|---|
| A.1 Test plan | [`docs/01_test_plan.md`](docs/01_test_plan.md) | 6 prioritised scenarios (TC-01…TC-06) with risk rationale |
| A.2 Execution and bugs | [`docs/02_execution_and_bugs.md`](docs/02_execution_and_bugs.md) | Top 3 scenarios executed, exploratory checks, 12 bug reports with evidence |
| B Automation | this repository | Framework, E2E UI test, API test, CI |
| C Strategy | [`docs/03_strategy_and_recommendations.md`](docs/03_strategy_and_recommendations.md) | Why these tests, what stays manual, recommendations |

The most serious findings (all Critical, all on the money path):

- **BUG-001** A negative stake is accepted and *increases* the balance.
- **BUG-002** The API accepts stakes above the balance; the balance goes negative.
- **BUG-003** The UI never refreshes the balance after a bet, so an ordinary user can bet
  money they no longer have.
- **BUG-004** A double click on Place Bet charges the stake twice and shows one receipt.
- **BUG-005** Bets on matches that have already been played are accepted.

## What's here

```
qa-betting-assignment/
├── README.md
├── requirements.txt               # runtime dependencies (pinned)
├── requirements-dev.txt           # + ruff, for lint
├── pyproject.toml                 # ruff configuration
├── pytest.ini                     # markers (api / ui), discovery, logging, output
├── conftest.py                    # run-wide hooks: report folder, test case ids, screenshots
├── .github/workflows/tests.yml    # CI: lint + tests on every push, report artifact
├── .env.example                   # BASE_URL, USER_ID, HEADLESS
├── framework/
│   ├── config.py                  # settings from env / .env, with defaults
│   ├── api/
│   │   ├── betting_client.py      # requests.Session wrapper, x-user-id auth, timeouts
│   │   └── models.py              # Pydantic models: Match + response contracts
│   ├── pages/                     # Page Object Model
│   │   ├── base_page.py           # explicit-wait helpers (no time.sleep)
│   │   ├── header.py              # balance pill
│   │   ├── match_list_page.py
│   │   ├── bet_slip.py
│   │   └── receipt_modal.py
│   └── utils/                     # shared helpers (reused across layers)
│       └── money.py               # parse_eur, expected_payout
├── tests/
│   ├── conftest.py                # shared fixtures: api_client, reset_balance, upcoming_match
│   ├── api/
│   │   └── test_stake_validation.py   # API business rule (parametrised boundaries)
│   └── ui/
│       ├── conftest.py                # UI fixtures: driver (Chrome)
│       └── test_place_bet_e2e.py      # E2E critical journey
├── docs/
│   ├── 01_test_plan.md
│   ├── 02_execution_and_bugs.md
│   ├── 03_strategy_and_recommendations.md
│   └── evidence/                  # curated bug screenshots (committed)
└── reports/                       # generated, one folder per run (git-ignored)
    └── <YYYY-MM-DD_HH-MM-SS>/
        ├── report.html            # pytest-html report, self-contained
        ├── junit.xml              # machine-readable results (CI)
        └── screenshots/           # failed / xfailed UI tests
```

## Tooling

Beyond the required stack (Python 3, Selenium WebDriver, pytest, requests):

| Tool | Why |
|---|---|
| `pydantic` | Validates API responses against the documented contract (see below). |
| `python-dotenv` | Loads the local `.env` so settings work without exporting variables by hand. |
| `pytest-html` | One-file HTML report with embedded screenshots; no server or extra CLI needed, unlike Allure. |
| `ruff` | Lint and formatting in one fast tool (dev only, `requirements-dev.txt`); enforced in CI. |
| GitHub Actions | Runs lint and the full suite on every push; see [CI](#ci). |

Dependencies are pinned in `requirements.txt`; no Poetry, to keep setup to one `pip install`.

## Requirements

- Python 3.11+ (uses `typing.Self`; 3.10 is end-of-life)
- Latest desktop Google Chrome (for the UI test). The matching driver is
  resolved automatically by **Selenium Manager** (bundled with Selenium 4.6+),
  so there is no separate driver download step.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt    # or requirements-dev.txt to also get ruff
cp .env.example .env               # then edit if needed
```

Configuration comes from environment variables. The project's `.env` file is loaded
automatically (python-dotenv), so editing `.env` is enough. Variables set in the shell or
in CI take precedence over `.env`, e.g. `HEADLESS=true pytest` runs headless whatever
`.env` says. `.env` is git-ignored; `.env.example` is the committed template.

| Variable   | Default                                   | Purpose                          |
|------------|-------------------------------------------|----------------------------------|
| `BASE_URL` | `https://qae-assignment-tau.vercel.app`   | App under test                   |
| `USER_ID`  | `candidate-hUyKPqFY2gaP`                  | Candidate user id (auth)         |
| `HEADLESS` | `true`                                    | Run Chrome headless or headed    |

## Running

Run every command from the project folder, with its `.venv` activated.

```bash
pytest                 # everything
pytest -m api          # API tests only (fast, no browser)
pytest -m ui           # UI E2E only
HEADLESS=false pytest -m ui   # watch the browser

ruff check . && ruff format --check .   # lint (needs requirements-dev.txt)
```

### Reports

Every run writes its own report to **`reports/<YYYY-MM-DD_HH-MM-SS>/report.html`**, so
earlier runs are kept for comparison; the path is printed at the end of the run. Pass
`--html=path/report.html` to write somewhere else. The report is a single self-contained
file, so it can be attached to a CI run or shared as is.

For each test the report shows:

| What | Logger | Example |
|---|---|---|
| Every API request and response | `api` | `→ POST /api/place-bet` with headers and body, `← 200 OK (582 ms)` with body |
| Every UI step and value read | `ui` | `click #bet-slip-place-bet`, `read #modal-success-payout = '€2.02'` |
| Contract checks | `contract` | `✘ PlaceBetResponseStrict` with each failing field |
| Browser console at teardown | `ui` | `browser console: 0 message(s)` |
| Screenshot of failed / xfailed UI tests | — | embedded image, also saved to `screenshots/` |

The `x-user-id` is masked in the logs, because it is the only credential. Logs go to the
report only (`log_level = INFO` in `pytest.ini`), so the terminal stays readable; add
`-o log_cli=true` to see them live.

Expected result against the live app today: **9 passed, 5 xfailed** (the xfails are
the known bugs listed below).

| Test | Result | Bug |
|---|---|---|
| API: stake boundaries (7 cases) | PASS | |
| API: negative stake rejected | XFAIL | BUG-001 |
| API: full response contract (EUR, payout = stake × odds) | XFAIL | BUG-008, BUG-009 |
| UI: bet placed, receipt shows the bet | PASS | |
| UI: stake deducted from the persisted balance | PASS | |
| UI: receipt matches the bet slip | XFAIL | BUG-006, BUG-010 |
| UI: displayed balance updated after the bet | XFAIL | BUG-003 |
| UI: double click on Place Bet places one bet | XFAIL | BUG-004 |

## The two automated tests

### API — `tests/api/test_stake_validation.py`
Parametrised boundary check of stake validation on `POST /api/place-bet`
(min €1.00, max €100.00, 2-decimal precision). For every rejected stake it
asserts the status code, that the error envelope matches the contract, **and**
that the persisted balance is unchanged — the part that actually protects the
ledger. Accepted responses are parsed through a **Pydantic** model
(`framework/api/models.py`) so the response *shape* (required fields + types) is
validated too, not just the status code. A separate `xfail` test parses through
the *strict* model (which also enforces `currency == EUR` and
`payout == stake × odds`) to pin the two contract bugs. Chosen because stake
validation is a money-path rule that must hold at the API layer independently of
the UI, it is fully deterministic, and it needs no browser.

**Why Pydantic (not a plain dataclass) for the response models:** the data comes
from an external API with known contract bugs, so runtime validation is the
point. A dataclass gives type *hints* but validates nothing at runtime; Pydantic
enforces required fields, types, unknown-field drift (`extra="forbid"`), and
cross-field business rules declaratively in one place. Plain dataclasses are
still the right choice for internal, trusted data structures — validation belongs
at the boundary with the untrusted source.

### UI — `tests/ui/test_place_bet_e2e.py`
The critical journey: select an outcome → enter a stake → place the bet → see the
receipt. Split into five tests: the journey completes with a receipt (passes),
the stake is deducted from the persisted balance, checked via `GET /api/balance`
(passes), the receipt shows the same payout and team order as the bet slip
(`xfail`, BUG-006 and BUG-010), the balance shown in the UI drops by the stake
(`xfail`, BUG-003; with the stale balance the UI lets a user bet money they no longer
have), and a double click on Place Bet places one bet (`xfail`, BUG-004). The double-click
test checks both the money (charged once) and the cause (the button must not accept a
second click while `Placing...`); the money check alone depends on server timing and
would be flaky, the button check is deterministic.

### Traceability to the test plan

Every test has a **unique test case id** `TC-<scenario>.<case>`, where the scenario is one
of the six in [`docs/01_test_plan.md`](docs/01_test_plan.md):
`@pytest.mark.testcase("TC-03.02")`. The id is shown next to the status in the terminal
(`PASSED [TC-03.02]`), as a column in the HTML report, in the CI summary, and in JUnit XML
as `testcase` and `scenario` properties (the format test management tools such as TestRail
or Xray import). A missing, malformed or duplicate id, or a scenario that is not in the
plan, stops the run at collection.

```bash
pytest -k "TC-03.02"           # one test
pytest -k "TC-03"              # every test of one scenario
pytest -k "TC-03 or TC-05"     # several scenarios
pytest -m api -k "TC-05"       # combine with the layer markers
```

| Id | Test | Result today |
|---|---|---|
| TC-01.01 | `test_place_bet_shows_receipt` | pass |
| TC-01.02 | `test_place_bet_deducts_stake` | pass |
| TC-01.03 | `test_receipt_matches_bet_slip` | xfail (BUG-006, BUG-010) |
| TC-01.04 | `test_displayed_balance_updates_after_bet` | xfail (BUG-003) |
| TC-01.05 | `test_double_click_places_one_bet` | xfail (BUG-004) |
| TC-03.01 – TC-03.05 | `test_stake_boundary_validation` `[below_min]` `[at_min]` `[just_above_min]` `[at_max]` `[above_max]` | pass |
| TC-05.01, TC-05.02 | `test_stake_boundary_validation` `[three_decimals]` `[zero]` | pass |
| TC-05.03 | `test_negative_stake_is_rejected` | xfail (BUG-001) |
| TC-06.01 | `test_place_bet_response_matches_full_contract` | xfail (BUG-008, BUG-009) |

Not automated, by choice (see the strategy note): **TC-02** stake above balance (covered
by BUG-002 / BUG-003 in the bug report) and **TC-04** error modal and Rebet (exploratory).

## CI

[`.github/workflows/tests.yml`](.github/workflows/tests.yml) runs on every push and pull
request (and manually):

- **lint** — `ruff check` and `ruff format --check`.
- **tests** — the full suite (API + UI, headless Chrome) on `ubuntu-latest`. A results
  table is written to the run's summary page, and `reports/` (HTML report, JUnit XML,
  screenshots) is uploaded as the **test-report** artifact.

Runs are queued one at a time (`concurrency: live-app-tests`), because every run uses the
same account on the live app. `USER_ID` and `BASE_URL` can be overridden with a repository
secret / variable; when they are not set, the defaults in `framework/config.py` are used.
