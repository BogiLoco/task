# Strategy & Recommendations

## 1. Why these two tests were automated

I picked one test per layer, where the risk is highest and the upkeep is low,
instead of many shallow tests.

**API test: stake validation (`POST /api/place-bet`).**
Stake rules protect money, and the spec says the API must enforce them, not only
the UI (Spec §4.1). The test is fast, stable and needs no browser. For every
rejected stake it checks two things: the API returns an error, and the balance
does not change. A wrong status code is a bug; money moving silently is worse.
It also guards the worst bug found: a negative stake increases the balance
(BUG-001).

**UI test: placing a bet, end to end.**
Placing a bet is the main user journey and where the money comes from. One run
covers everything the user touches: choosing an outcome, entering a stake, the
payout, the "Placing…" state, the receipt and the balance. I automated only this
one journey, because UI tests cost the most to maintain. The same journey also
checks the two worst bugs a normal user can hit by clicking: the balance on screen
does not update after a bet, so the user can bet money they no longer have
(BUG-003), and a double click charges the stake twice (BUG-004).

Together they follow the test pyramid: the cheap API test covers most business
rules, and one UI test proves the parts work together for a real user.

## 2. What stays manual, and why

- **Error modal and Rebet (TC-04).** The app has no way to force an error. During
  exploration I faked a `500` in the browser, which showed that the modal and its
  buttons work. But that only tests the frontend against a fake server, not real
  failures such as timeouts or a bet that went through while the response was
  lost. So it stays exploratory until the app offers a way to force errors (see
  recommendation 2).
- **Exact texts and layout.** Wording, symbols and styling change often, carry
  little risk and are quick to check by eye. Automated checks for them break often
  and catch little.
- **Filters (date and odds, Spec §2.6).** They do not touch money, and the spec
  does not define their edge cases (for example, whether one matching odd is
  enough). Better tested by hand until the rules are clear.
- **User isolation and auth.** I checked the basics: a missing, empty or unknown
  `x-user-id` returns `401`, and `?user-id=` alone does not authenticate API calls.
  The user id is the only credential and it travels in the URL, so it ends up in
  browser history and server logs. That is fine for a test environment, not for
  production, which needs real session or token auth. Deeper checks (guessing ids,
  one user changing another user's balance) belong in a one-off security review,
  not in the daily regression suite.

Automating these now would add upkeep and flaky tests without protecting anything
important.

## 3. Recommendations if the project grows

**1. Test data per worker, so CI can run in parallel.**
CI already runs lint and all tests on every push and publishes the reports. Next,
run the API tests on every pull request and the slower UI tests nightly. Today all
tests share one user, and the API allows only one bet per user at a time, so tests
cannot run in parallel. The fix is a pool of test users (one per worker or per
test), ideally with an endpoint that sets up a known state for each test. When run
history and trends start to matter, switch the report to Allure.

**2. A way to force errors.**
Add a test-only switch (a feature flag, a special stake value or a header) that
makes `place-bet` fail on purpose. Then TC-04 can be automated, including the most
important check: Rebet must not charge twice. This one change would unlock the most
new tests, and it targets a real money risk.

**3. Contract tests and a clearer spec.**
Several bugs are contract bugs: the bet response says `USD` instead of `EUR`
(BUG-008), the reset response does not match the saved balance (BUG-007), and the
Swagger examples do not match the real errors (BUG-012). A contract test generated
from the OpenAPI file (`/api/docs?format=json`, e.g. with Schemathesis) would catch
these automatically. The spec should also settle:

- the minimum stake (€1.00 or €1.01; the spec says both),
- how the payout is rounded,
- how to make Rebet safe (an idempotency key per bet),
- when the API returns `400` and when `422`,
- stable `data-testid` attributes in the UI, so locators survive markup changes.
