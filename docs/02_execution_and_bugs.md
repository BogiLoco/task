# Execution Results & Bug Reports

**Application:** Sports Betting QA Assessment App
**Base URL:** `https://qae-assignment-tau.vercel.app`
**User context:** `x-user-id: candidate-hUyKPqFY2gaP`
**Date of execution:** 2026-11-12 / 2026-11-13
**Spec references:** *Feature Specification – Single Bet Placement* ("Spec") and the
*Home Assignment – Domain Context* ("Domain Context").

---

## 1. Summary — bugs by severity

Bugs are numbered in order of severity, most severe first.

| ID | Title | Severity | Layer |
|---|---|---|---|
| BUG-001 | Negative stake is accepted and increases the balance | **Critical** | API |
| BUG-002 | Stake exceeding the balance is accepted by the API; balance goes negative | **Critical** | API |
| BUG-003 | Displayed balance is not updated after a bet, so the UI lets the user bet money they no longer have | **Critical** | UI + API |
| BUG-004 | Double-clicking Place Bet places the bet twice; one receipt is shown | **Critical** | UI + API |
| BUG-005 | Bets are accepted on past (already-played) matches | **Critical** | API + UI + data |
| BUG-006 | Receipt shows a wrong potential payout (stake × 2 instead of stake × odds) | **High** | UI (receipt) |
| BUG-007 | `reset-balance` response ≠ persisted balance; €125.50 not restored | **High** | API |
| BUG-008 | `place-bet` returns `currency: "USD"` instead of EUR | **High** | API |
| BUG-009 | API truncates payout instead of rounding (€348.49 instead of €348.50) | **Medium** | API |
| BUG-010 | Home/away teams reversed on the receipt | **Medium** | UI (receipt) |
| BUG-011 | Protocol errors not handled per spec: malformed JSON → 500, `GET /api/place-bet` → 200 | **Low** | API |
| BUG-012 | Swagger shows `insufficient_balance` as the example for 405 / 409 / 500 | **Low** | Docs |

The highest-impact issues all sit on the **money path**. The API enforces neither the sign
of the stake nor the available balance, so a user can create money (negative stakes) or
spend money they do not have (unlimited overdraft). The UI does not close that gap: it
checks the stake against a balance that is never refreshed after a bet, so an ordinary user
can overdraw just by clicking, and a double click on Place Bet charges the stake twice while
showing one receipt. The API also accepts bets on events with a known outcome.
Separately, the receipt, which is the user's record of the bet, promises a different payout
from the one quoted before placement.

**Severity scale:** Critical: direct, exploitable financial loss or integrity failure ·
High: wrong money values or broken contract on the core path · Medium: small monetary
error or wrong non-monetary information shown to the user · Low: documentation / cosmetic.

---

## 2. Scope of execution

The three highest-priority planned scenarios (TC-01, TC-02, TC-03) were executed in the UI
and directly against the API with `curl`, followed by exploratory checks focused on the
money path (stake validation, balance integrity, payout, event eligibility) and the API
contract. The API was exercised directly because the spec requires validation to hold at
the API layer, not only in the UI (Spec §4.1, "UI + API").

```bash
U='x-user-id: candidate-hUyKPqFY2gaP'
B='https://qae-assignment-tau.vercel.app'
M='premier-league-manutd-chelsea'
```

Exploratory checks on 2026-11-13 also covered: auth and user isolation, `selection` /
`matchId` / stake-type validation, protocol errors, concurrent requests, what the UI actually
sends to the API (requests captured in the browser), double-clicking Place Bet, and the error
modal. The error path (TC-04) cannot be triggered from the UI on its own, so it was exercised
by replacing the browser's `fetch` response for one request with a `500`.

### Executed planned scenarios

| Scenario | Result | Notes |
|---|---|---|
| TC-01 Valid single bet; balance and receipt verified | **Fail** | Placement works, the stake is deducted on the server and the bet slip is correct. But the displayed balance is not updated (BUG-003), the receipt payout is wrong (BUG-006), teams are reversed (BUG-010), currency is USD (BUG-008), and the balance baseline is wrong after reset (BUG-007). |
| TC-02 Stake exceeding balance rejected (UI + API) | **Fail** | The API accepts a stake larger than the balance (BUG-002). The UI accepts it too after an earlier bet in the same session, because it checks against a stale balance (BUG-003). |
| TC-03 Stake boundary values | **Pass (positive side)** | `0.99`, `100.01`, `0`, `0.5`, `500`, `10.555` correctly rejected; `1.00`, `1.01`, `100.00` accepted. Negative values are the gap (BUG-001). |

### Stake validation boundary, as observed (API)

| Input | Response | Verdict |
|---|---|---|
| `-50` | `200 Bet placed successfully`, balance increases | **Defect (BUG-001)** |
| `0` | `422 invalid_stake_min` | Correct |
| `0.5` | `422 invalid_stake_min` | Correct |
| `0.99` | `422 invalid_stake_min` | Correct |
| `1.00` / `1.01` | `200`, balance reduced by the stake | Correct (lower boundary) |
| `100.00` | `200`, balance reduced by the stake | Correct (upper boundary) |
| `100.01` | `422 invalid_stake_max` | Correct |
| `500` | `422 invalid_stake_max` | Correct |
| `10.555` | `422 invalid_stake_precision` | Correct |
| `"10"` (string) | `422 invalid_stake_type` | Correct |
| `85` with balance `32` | `200`, balance becomes `-53` | **Defect (BUG-002)** |

The per-bet stake limits (min, max, precision, type) are enforced, but two rules are missing
entirely on the server: the stake must be positive, and it must not exceed the balance.

### Verified as working

- **Place Bet button** is disabled until a valid stake is entered, then enables and places
  the bet (expected behaviour).
- **Bet slip payout is correct:** €1.01 × 2.45 → €2.47; €9.99 × 2.80 → €27.97.
- **The stake is deducted from the persisted balance** when a bet is placed, in the API and
  through the UI (`GET /api/balance` 120 → 110 after a €10 UI bet).
- **Closing the receipt** returns to the match list with an empty bet slip (Spec §2.4).
- **Odds data is in range:** all catalogue odds fall within 1.35–7.50 (rule: 1.01–1000.00).
- **Extra request fields are ignored:** sending `"odds":1000,"payout":99999` had no effect.
- **Unknown `matchId`** returns `422 invalid_match`; blank or missing `matchId` returns
  `422 invalid_match_id`. Invalid `selection` (`home`, `X`, `1`, empty, missing) returns
  `422 invalid_selection`; stake `null`, `true`, `[10]`, `"10"` or missing returns
  `422 invalid_stake_type`.
- **Auth:** missing, empty or unknown `x-user-id` returns `401`; `?user-id=` alone does not
  authenticate API calls. `PUT` / `DELETE` / `PATCH` on `place-bet` return `405`.
- **Concurrent API requests:** of 6 parallel €10 bets, 2 were accepted and 4 rejected with
  `409 bet_in_progress`; the balance dropped by exactly €20 (no lost update).
- **The UI sends what the user selected:** clicking `1` / `X` / `2` sends `HOME` / `DRAW` /
  `AWAY` with the right `matchId` and stake; the receipt odds match.
- **Stake input:** `-5` is stored as `5`, `abc` is rejected, `12,50` becomes `12.50`,
  `12.345` is cut to `12.34`. Above €100, below €1 and above the (displayed) balance the UI
  shows "Maximum stake is €100.00", "Minimum stake is €1.00" and "Insufficient balance" and
  disables Place Bet (Spec §4.4).
- **Error modal (TC-04):** title "Something went wrong", body asks to try again, buttons
  Rebet / Close / X. Rebet retries and charges once; Close and X clear selection and stake
  (Spec §2.5). Evidence: `docs/evidence/TC-04_error_modal.png`.
- **OpenAPI JSON** (`/api/docs?format=json`, Spec §5.2) returns `200` with
  `Content-Type: application/json` (OpenAPI 3.0.3).

---

## 3. Bug Reports

### BUG-001: Negative stake is accepted and increases the user's balance

- **Severity:** Critical
- **Affected endpoint:** `POST /api/place-bet`

**Reproduction steps:**

```bash
curl -s -X POST "$B/api/reset-balance" -H "$U"; echo
curl -s "$B/api/balance" -H "$U"; echo
curl -s -X POST "$B/api/place-bet" -H "$U" -H 'Content-Type: application/json' \
  -d "{\"matchId\":\"$M\",\"selection\":\"HOME\",\"stake\":-50}"; echo
curl -s "$B/api/balance" -H "$U"; echo
```

**Expected:** `422` validation error. The stake must be a positive value of at least €1.00
(Spec §4.1, "positive values"). Balance unchanged.

**Actual:** `200 "Bet placed successfully"` with `"stake":-50`, `"payout":-122.51`. Balance
**increased** by 50 (120 → 170).

```
{"balance":120,"currency":"EUR"}
{"message":"Bet placed successfully","matchId":"premier-league-manutd-chelsea","selection":"HOME","stake":-50,"odds":2.45,"payout":-122.51,"balance":170,"currency":"USD"}
{"balance":170,"currency":"EUR"}
```

**Business impact:** Any user can inflate their balance without limit by placing
negative-stake bets. This is a direct, unbounded financial loss for the operator, reachable
through the public API without the UI.

**Evidence:** raw `curl` output above. Automated: `tests/api/test_stake_validation.py::test_negative_stake_is_rejected` (xfail).

---

### BUG-002: Stake exceeding the balance is accepted by the API; balance goes negative

- **Severity:** Critical
- **Affected endpoint:** `POST /api/place-bet`

**Reproduction steps** (starting balance €52, as returned by `GET /api/balance`):

```bash
M2='ligue-1-marseille-psg-2026-11-17'
curl -s "$B/api/balance" -H "$U"; echo
for s in 10 10 85 10; do
  curl -s -X POST "$B/api/place-bet" -H "$U" -H 'Content-Type: application/json' \
    -d "{\"matchId\":\"$M2\",\"selection\":\"HOME\",\"stake\":$s}"; echo
  curl -s "$B/api/balance" -H "$U"; echo
done
```

**Expected:** A stake greater than the available balance is rejected with `422`
(insufficient balance) and the balance is unchanged (Domain Context: the stake "cannot exceed
the user's current balance"; Spec §4.1 "UI + API"; Spec §4.4 "Insufficient balance").

**Actual:** A €85 bet with a balance of €32 was accepted and the balance dropped to **−53**.
A further €10 bet at −53 was also accepted (balance −63).

```
{"balance":52,"currency":"EUR"}
... stake 10 -> "balance":42 ... stake 10 -> "balance":32
{"message":"Bet placed successfully","matchId":"ligue-1-marseille-psg-2026-11-17","selection":"HOME","stake":85,"odds":4.1,"payout":348.49,"balance":-53,"currency":"USD"}
{"balance":-53,"currency":"EUR"}
{"message":"Bet placed successfully","matchId":"ligue-1-marseille-psg-2026-11-17","selection":"HOME","stake":10,"odds":4.1,"payout":41,"balance":-63,"currency":"USD"}
{"balance":-63,"currency":"EUR"}
```

**UI vs API:** After a fresh page load the UI shows the real balance and blocks a stake above
it, so the check exists in the frontend but is missing on the server. The frontend check is
not reliable either: it uses a balance that is not refreshed after a bet (BUG-003).

**Business impact:** Users can place bets with money they do not have, an unlimited
overdraft. Combined with winning payouts, the operator pays out on stakes that were never
funded. A frontend-only check gives no protection because the API is public and can be
called directly.

**Evidence:** raw `curl` output above.

---

### BUG-003: Displayed balance is not updated after a bet, so the UI lets the user bet money they no longer have

- **Severity:** Critical
- **Affected area:** UI, header balance (`#header-balance`) and bet slip balance
  (`#bet-slip-balance`); combined with the missing server-side check (BUG-002)

**Reproduction steps** (UI only, no page reload between steps):

1. Reset the balance: `curl -s -X POST "$B/api/reset-balance" -H "$U"`. `GET /api/balance` returns `120`.
2. Open the app with `?user-id=candidate-hUyKPqFY2gaP`. The header shows **Balance: €120.00**.
3. On **Marseille vs PSG** select `1` (odds 4.10), enter `100`, click **Place Bet**, then **Close**.
4. Note the header and bet slip balance, and `GET /api/balance`.
5. Select `1` on the same match again, enter `50`, click **Place Bet**.
6. Reload the page, or call `GET /api/balance`.

**Expected:** After a bet the displayed balance drops by the stake (Domain Context: the
balance "decreases by the stake amount when a bet is placed" and "is shared across the header
and the bet slip"; Spec §2.3 "On success: stake is deducted"). In step 5 the €50 stake exceeds
the real balance of €20, so the UI shows **Insufficient balance** and blocks the bet (Spec §4.1, §4.4).

**Actual:**

| Step | Header / bet slip | `GET /api/balance` |
|---|---|---|
| 2. Page loaded | €120.00 | 120 |
| 4. After the €100 bet | **€120.00** | 20 |
| 5. €50 bet | accepted, success receipt shown | **−30** |
| 6. After reload | shows the real balance | −30 |

The displayed balance is never updated after a bet (still unchanged after an explicit 8 s
wait); only a full page reload shows the real value. Because the UI's insufficient-balance
check uses that stale value, the €50 bet passes the UI, and the API accepts it because it
does not check the balance at all (BUG-002).

**Business impact:** An ordinary user, using only the UI, can stake money they do not have
and drive the balance negative. BUG-002 on its own needs direct API calls; together with
this defect the overdraft is reachable on the main user journey. The user is also shown
money they no longer have, which leads to disputes when the real balance appears.

**Evidence:** `docs/evidence/BUG-003_1_balance_not_refreshed.png` (header €120.00 after a
€1.01 bet while `GET /api/balance` returned `118.99`);
`docs/evidence/BUG-003_2_overdraft_via_ui_receipt.png` (success receipt for the €50 bet,
header still €120.00, real balance €20 before the bet). Automated:
`tests/ui/test_place_bet_e2e.py::test_displayed_balance_updates_after_bet` (xfail).

---

### BUG-004: Double-clicking Place Bet places the bet twice; one receipt is shown

- **Severity:** Critical
- **Affected area:** UI, Place Bet button (`#bet-slip-place-bet`); API `POST /api/place-bet`

**Reproduction steps:**

1. Reset the balance and open the app with `?user-id=candidate-hUyKPqFY2gaP`.
2. Select `1` on **Ajax vs AZ Alkmaar** (odds 1.85) and enter a stake of `2`.
3. Double-click **Place Bet** (a normal mouse double click; two single clicks 150 ms apart give
   the same result).
4. Close the receipt and check `GET /api/balance`.

**Expected:** One bet is placed and €2 is deducted. After the first click the button enters the
loading state (`Placing...`) and ignores further clicks until the bet resolves to one final
outcome (Spec §2.3). The server rejects a second bet while one is in progress (`409`, Spec §5.3).

**Actual:** The UI sends two `POST /api/place-bet` requests, both return `200 Bet placed
successfully`, and **€4 is deducted**. Only **one** success receipt is shown, so the user does
not know a second bet was placed. Reproduced 4 out of 4 times:

| Attempt | Requests sent | Responses | Receipts shown | Balance |
|---|---|---|---|---|
| 1 | 2 | 200, 200 | 1 | 120 → 116 |
| 2 | 2 | 200, 200 | 1 | 116 → 112 |
| 3 | 2 | 200, 200 | 1 | 112 → 108 |
| 4 (two clicks 150 ms apart) | 2 | 200, 200 | 1 | 108 → 104 |

**Root-cause indication:** While the bet is being placed the button shows `PLACING...` (class
`placeBetButtonPlacing`) but is **not disabled**, so the second click submits again. The
server-side `409 bet_in_progress` guard does not catch it either: both requests succeed.

**Business impact:** Users are charged twice for one intended bet, and the receipt hides it.
Double-clicking a submit button is common, so this hits ordinary users on the main journey.
It leads to unexpected losses, chargebacks and complaints, and duplicate bets distort the
operator's liability on the event.

**Evidence:** `docs/evidence/BUG-004_double_click_one_receipt.png` (one receipt for €2 while
the server had accepted two €2 bets); request and response log above (captured in the browser).
Automated: `tests/ui/test_place_bet_e2e.py::test_double_click_places_one_bet` (xfail).

---

### BUG-005: Bets are accepted on past (already-played) matches

- **Severity:** Critical
- **Affected endpoints:** `GET /api/matches`, `POST /api/place-bet`

**Context:** Today is 2026-11-13. The catalogue returned by `GET /api/matches` contains ~98
matches, the large majority with a `kickoffDate` in the past (from 2026-02-27). The UI
itself labels them with a **PAST** badge. Only matches from 2026-11-13 onward are upcoming.

**Reproduction steps:**

```bash
curl -s "$B/api/matches" -H "$U"; echo        # inspect kickoffDate values
curl -s -X POST "$B/api/place-bet" -H "$U" -H 'Content-Type: application/json' \
  -d '{"matchId":"la-liga-real-barca","selection":"HOME","stake":10}'; echo
```

**Expected:** Only upcoming, pre-match events are listed and bettable (Spec §1 and §3,
"Upcoming matches only"). A bet on a match whose kickoff is in the past is rejected.

**Actual:** Past matches are listed and accepted for betting. `la-liga-real-barca`
(kickoff 2026-02-27) returned `200`:

```
{"message":"Bet placed successfully","matchId":"la-liga-real-barca","selection":"HOME","stake":10,"odds":1.85,"payout":18.5,"balance":110,"currency":"USD"}
```

The same holds for `premier-league-manutd-chelsea` (kickoff 2026-02-27). Every bet on it
succeeded during testing.

**Also in the UI:** a match with the **PAST** badge (`serie-a-juventus-roma-2026-11-09`) can
be selected, Place Bet is enabled, and the bet is accepted with a success receipt.

**Business impact:** Accepting bets on events whose outcome is already known enables
guaranteed-win abuse, a critical integrity failure for a betting product. Two matches from
different leagues confirm it is systemic (no event-date/status validation), not one bad record.

**Evidence:** catalogue dump; `curl` output above; PAST badge visible in the UI.

---

### BUG-006: Receipt shows a wrong potential payout (stake × 2 instead of stake × odds)

- **Severity:** High
- **Affected area:** UI, success receipt modal

**Reproduction steps:**

1. Open the app with `?user-id=candidate-hUyKPqFY2gaP`.
2. On **Derby County vs Norwich**, select the Home outcome (`1`, odds 2.45).
3. Enter a stake of `1.01`. The bet slip shows **Potential Payout €2.47**.
4. Click **Place Bet**.
5. Read the payout on the "Bet Placed Successfully!" receipt.

**Expected:** The receipt payout equals stake × odds (€1.01 × 2.45 = €2.47) and matches the
value shown before placement (Domain Context: "All values should be consistent with what was
shown before placement"; Spec §2.4).

**Actual:** The receipt shows **Stake €1.01, Odds 2.45, Potential Payout €2.02**. The payout
contradicts both the odds on the receipt itself and the bet slip.

| | Bet slip | API response | Receipt |
|---|---|---|---|
| Stake | €1.01 | 1.01 | €1.01 |
| Odds | 2.45 | 2.45 | 2.45 |
| Payout | **€2.47** ✅ | **2.47** ✅ | **€2.02** ❌ |

The API computes the payout correctly for the same bet:

```bash
curl -s -X POST "$B/api/place-bet" -H "$U" -H 'Content-Type: application/json' \
  -d '{"matchId":"championship-derby-norwich-2026-11-27","selection":"HOME","stake":1.01}'; echo
```
```
{"message":"Bet placed successfully","matchId":"championship-derby-norwich-2026-11-27","selection":"HOME","stake":1.01,"odds":2.45,"payout":2.47,"balance":106.97,"currency":"USD"}
```

**Root-cause indication:** The receipt shows **stake × 2** regardless of the odds. Confirmed
on other matches and outcomes:

| Bet | Bet slip (correct) | Receipt |
|---|---|---|
| €1.01 × 2.45 | €2.47 | €2.02 (= 1.01 × 2) |
| €10 × 4.10 | €41.00 | €20.00 (= 10 × 2) |
| €100 × 4.10 | €410.00 | €200.00 (= 100 × 2) |
| €3.33 × 1.85 | €6.16 | €6.66 (= 3.33 × 2) |

The backend and the bet slip are correct, so the receipt recalculates the payout client-side
with a fixed multiplier instead of displaying the odds-based value. The error can go either
way: below the real payout for odds above 2 and above it for odds below 2.

**Business impact:** The receipt is the user's record of the bet. It promises a different
payout from the one quoted before placement, by up to half the payout (€200 instead of €410),
which creates disputes ("which amount will I be paid?") and damages trust on the core revenue
flow. Where it overstates the payout (odds below 2), the user holds a record of a promise the
operator will not honour.

**Evidence:** `docs/evidence/BUG-006_BUG-010_1_bet_slip_before.png` (slip: €2.47),
`docs/evidence/BUG-006_BUG-010_2_receipt_after.png` (receipt: €2.02); `curl` output above.
Automated: `tests/ui/test_place_bet_e2e.py::test_receipt_matches_bet_slip` (xfail).

---

### BUG-007: `reset-balance` response does not match persisted state

- **Severity:** High
- **Affected endpoints:** `POST /api/reset-balance`, `GET /api/balance`

**Reproduction steps:**

```bash
curl -s -X POST "$B/api/reset-balance" -H "$U"; echo   # response
curl -s "$B/api/balance" -H "$U"; echo                 # persisted state
```

**Expected:** The reset response, `GET /api/balance`, and the UI show the same value, equal
to the initial balance of €125.50 (Spec §5.3: "Response body and persisted state must be
consistent after reset"; Domain Context: balance starts at €125.50).

**Actual:** The reset response returns `"balance":125.5`, but `GET /api/balance` immediately
afterward returns `120`, and the UI header shows €120.00. Reproduced again on 2026-11-13.

```
{"message":"Balance reset successfully","balance":125.5,"currency":"EUR"}
{"balance":120,"currency":"EUR"}
```

**Business impact:** The API reports a balance the user does not have. Any client that trusts
the reset response (support tools, test fixtures) works with a wrong figure, and the user
starts €5.50 below the documented balance.

**Note:** (a) *response ≠ persisted state* is a hard violation of Spec §5.3; (b) *€125.50 as
the correct value* comes from Domain Context, since §5.3 only says "initial configured value".
The Swagger description itself states "response payload may differ from persisted balance",
which contradicts the spec.

**Evidence:** `curl` output above; Swagger description of the 200 response.

---

### BUG-008: `place-bet` returns `currency: "USD"` instead of EUR

- **Severity:** High
- **Affected endpoint:** `POST /api/place-bet`

**Reproduction steps:**

```bash
curl -s -X POST "$B/api/place-bet" -H "$U" -H 'Content-Type: application/json' \
  -d "{\"matchId\":\"$M\",\"selection\":\"HOME\",\"stake\":10}"; echo
```

**Expected:** `"currency":"EUR"`. The spec and Domain Context denominate all money in euros,
and `GET /api/balance` and `POST /api/reset-balance` both return `"EUR"`.

**Actual:** Every successful bet response returns `"currency":"USD"` (observed on all bets
during testing).

```
{"message":"Bet placed successfully", ... ,"balance":110,"currency":"USD"}
```

**Business impact:** Inconsistent currency within one API on the money path. A client reading
currency from the bet response would display or record the wrong denomination.

**Evidence:** `curl` output above; contrast with `EUR` from `balance` and `reset-balance`.
Automated: `tests/api/test_stake_validation.py::test_place_bet_response_matches_full_contract` (xfail).

---

### BUG-009: API truncates payout instead of rounding it

- **Severity:** Medium
- **Affected endpoint:** `POST /api/place-bet`

**Reproduction steps:**

```bash
curl -s -X POST "$B/api/place-bet" -H "$U" -H 'Content-Type: application/json' \
  -d '{"matchId":"ligue-1-marseille-psg-2026-11-17","selection":"HOME","stake":85}'; echo
```

**Expected:** Payout = stake × odds rounded to 2 decimals: €85 × 4.10 = **€348.50**.

**Actual:** `"payout":348.49`. Re-checked on 2026-11-13 on the same match (odds 4.10):

| Stake | Expected payout | API payout |
|---|---|---|
| 1.00 | 4.10 | **4.09** ❌ |
| 10 | 41.00 | 41 ✅ |
| 85 | 348.50 | **348.49** ❌ |
| 100 | 410.00 | **409.99** ❌ |

**Root-cause indication:** In binary floating point 4.1 is slightly below 4.1, so
1 × 4.1 × 100 = 409.99999…, and the result is truncated (floored) to 2 decimals instead of
rounded. The same pattern appears in BUG-001: −50 × 2.45 = −122.50, but the API returned
−122.51 (floor of a negative number). Products that happen to land on an exact float, such
as 10 × 4.1 = 41, come out right, which is why the issue only shows on some amounts.

**Business impact:** Users are underpaid by €0.01 on affected stakes. Small per bet, but
systematic, and incorrect monetary arithmetic is a compliance concern for a regulated
product. Money should be computed in integer cents or a decimal type, with an explicit
rounding rule.

**Evidence:** `curl` output above. Automated: covered by the same xfail contract test as BUG-008.

---

### BUG-010: Home/away teams are reversed on the receipt

- **Severity:** Medium
- **Affected area:** UI, success receipt modal

**Reproduction steps:** Same bet as BUG-006 (Home on Derby County vs Norwich, stake €1.01),
then compare the match name in the bet slip with the receipt.

**Expected:** The home team is listed first everywhere, including the receipt (Domain Context:
"Home team is always listed first … carries through to the receipt"). The catalogue has
`homeTeam: "Derby County"`, `awayTeam: "Norwich"`.

**Actual:** Bet slip shows **"Derby County vs Norwich"**; the receipt shows
**"Norwich vs Derby County"**. Also reproduced on Marseille vs PSG (receipt: "PSG vs Marseille").

**Business impact:** The receipt misrepresents the fixture. With a Home selection, a reversed
fixture makes the user believe they backed the other team. No money moves, but it undermines
the bet record and will generate support contacts.

**Note:** Like BUG-006 this is a receipt-only defect. The API returns only `matchId` and
`selection`, so the frontend builds the team order itself.

**Evidence:** `docs/evidence/BUG-006_BUG-010_1_bet_slip_before.png` (slip: "Derby County vs
Norwich"), `docs/evidence/BUG-006_BUG-010_2_receipt_after.png` (receipt: "Norwich vs Derby
County"). Automated: same xfail test as BUG-006.

---

### BUG-011: Protocol errors are not handled as specified

- **Severity:** Low
- **Affected endpoint:** `/api/place-bet`

**Reproduction steps:**

```bash
curl -s -w ' [%{http_code}]\n' -X POST "$B/api/place-bet" -H "$U" \
  -H 'Content-Type: application/json' -d '{"matchId":'
curl -s -w ' [%{http_code}]\n' "$B/api/place-bet" -H "$U"
```

**Expected:** A malformed JSON body is rejected with `400 invalid_json` (Spec §4.3 and §5.3;
the Swagger documents this exact error). An unsupported method returns `405` (Spec §4.3).

**Actual:**

| Request | Expected | Actual |
|---|---|---|
| `POST` with truncated JSON `{"matchId":` | `400 invalid_json` | `500 internal_server_error` |
| `POST` with `"stake":NaN` (not valid JSON) | `400 invalid_json` | `500 internal_server_error` |
| `GET /api/place-bet` | `405 method_not_allowed` | `200 {}` |

`PUT`, `DELETE` and `PATCH` correctly return `405`, and a non-object body (`[1,2]`) correctly
returns `400 invalid_request`.

**Business impact:** No money moves, but a client error is reported as a server failure,
which triggers false alerts and hides real 500s in monitoring. A `200` on `GET` suggests the
endpoint did something, which can mislead clients and probes.

**Evidence:** `curl` output above.

---

### BUG-012: Swagger shows `insufficient_balance` as the example for 405 / 409 / 500

- **Severity:** Low
- **Affected artifact:** `/api/docs`

**Finding:** In Swagger UI the **405**, **409** and **500** responses of `POST /api/place-bet`
all show `{"error":"insufficient_balance","message":"Insufficient balance"}`. These responses
have no example of their own (`/api/docs?format=json`), so Swagger UI falls back to the example
on the shared `Error` schema, which is `insufficient_balance`. The API never returns that code:
a stake above the balance is accepted (BUG-002), a second bet in progress returns
`bet_in_progress`, a wrong method `method_not_allowed`, and a server failure
`internal_server_error`.

**Expected:** Each error response shows its real error code, and `insufficient_balance` is
documented only once the API enforces the balance rule.

**Business impact:** A client built to the documentation would handle the wrong error codes,
and the docs suggest a balance check that does not exist.

**Evidence:** Swagger UI for `POST /api/place-bet`; `components.schemas.Error` in
`/api/docs?format=json`.

---

## 4. Specification ambiguities (not bugs)

Recorded separately because the spec itself is unclear or contradictory:

- **Minimum stake:** Business Rules and UI copy say €1.00; the §4.1 table says €1.01. The API
  schema (`minimum: 1`) and observed behaviour treat €1.00 as valid.
- **Selection on the receipt:** Spec §2.4 lists "Selection" as a required receipt field, but
  the Domain Context description of the receipt (bet ID, match, stake, odds, potential payout,
  timestamp) does not. The live receipt has no selection field. Combined with BUG-010 the
  receipt gives no reliable way to tell which outcome was backed, so this should be clarified.
- **Bet ID origin:** the receipt shows a Bet ID (e.g. `#B-67099`), but the API response
  contains no bet id or timestamp, so the ID appears to be generated client-side and cannot be
  traced to a server record.
- **Kickoff time:** the API provides only `kickoffDate` (no time), while Spec §2.1 mentions a
  "kickoff date/time label".
- **Rebet after a lost response (idempotency):** if `place-bet` succeeds on the server but the
  response is lost (timeout, dropped connection), the UI shows the error modal and Rebet places
  the bet again. Simulated by letting the real request through and returning `500` to the UI:
  the balance dropped by twice the stake (€4 bet → €8). The spec defines Rebet as "retries
  placement" and says nothing about idempotency, so this is recorded as a risk rather than a
  bug; an idempotency key per bet attempt would fix it.
- **Payout rounding:** the rounding rule is not specified (see BUG-009 for observed behaviour).
