# Test Plan — Single Bet Placement

**Feature:** Single Bet Placement
**Application:** Sports Betting QA Assessment App (`https://qae-assignment-tau.vercel.app`)
**Scope:** Pre-match single bets, soccer only, desktop web (per *Feature Specification §1*).
**Out of scope:** live betting, accumulators, other sports, mobile UX (per spec §1).

## How this plan is built

Six scenarios were selected to span **happy path**, **negative/validation**, and **boundary**
cases. Priority is driven by **risk to money and trust** — the bet placement flow is the core
revenue path, so scenarios that touch the balance, the amount charged, or the amount paid out are
rated highest. Lower-risk areas (filters, cosmetic copy) are deliberately left at lower priority
and justified as such, rather than padded to inflate coverage.

Expected results below describe **correct behaviour per the specification**. Defects actually
observed during execution are recorded separately in `02_execution_and_bugs.md`.

Priority scale: **Critical** (blocks release / direct financial loss) > **High** (core rule, high
likelihood or impact) > **Medium** (contributes to integrity, lower likelihood) > **Low**
(cosmetic / low impact).

---

## TC-01 — Place a valid single bet and verify balance and receipt

- **Priority:** Critical
- **Type:** Happy path
- **Risk rationale:** This is the primary revenue path. If a correct bet is deducted wrongly, or
  the receipt shows values that differ from what was offered before placement, the user is charged
  or promised the wrong amount — a direct financial and trust failure. It also exercises the
  stake-deduction, payout calculation, and receipt-consistency rules in one flow.

- **Preconditions:** Authenticated via a valid `user-id`; balance reset to the initial €125.50;
  at least one upcoming match available.

- **Steps:**
  1. Open the app with a valid `?user-id=`.
  2. Note the displayed balance (expected €125.50).
  3. Select the HOME outcome (`1`) on an upcoming match; note the odds shown on the button.
  4. In the bet slip, enter a stake of €10.00.
  5. Note the potential payout shown in the slip before placing.
  6. Click **Place Bet** and wait for the flow to resolve.
  7. Inspect the success receipt.

- **Expected result:**
  - Button enters a `Placing...` in-progress state, then resolves to a single success outcome
    (Spec §2.3).
  - Stake is deducted: balance becomes €115.50, consistently in both header and bet slip
    (Domain Context — balance shared across header and bet slip).
  - Receipt shows all required fields (Spec §2.4): Bet ID, match details, selection, stake, odds
    at placement, potential payout, timestamp.
  - Payout = stake × odds (e.g. €10 × 2.45 = €24.50), and every receipt value matches what was
    shown before placement (Domain Context — "All values should be consistent").
  - Home/away order in the receipt matches the match list (Domain Context — home team listed first).
  - Currency is EUR (€) throughout.
  - Closing the receipt returns to the main flow with no active selection (Spec §2.4).

---

## TC-02 — Stake exceeding available balance is rejected (UI and API)

- **Priority:** Critical
- **Type:** Negative / validation
- **Risk rationale:** A bet larger than the balance means the user wagers money they do not have.
  The rule must hold at the API layer, not only in the UI, because the API is reachable directly
  and is the real guard on funds (Spec §4.1 — "UI + API"). A failure here lets the balance go
  negative or lets value be created from nothing.

- **Preconditions:** Balance reset to €125.50.

- **Steps (UI):**
  1. Select an outcome on an upcoming match.
  2. A single stake cannot exceed the starting balance (€125.50 is above the €100 per-bet cap),
     so first place a €100 bet to lower the balance to €25.50.
  3. Select an outcome again, enter a stake of €50 and try to place the bet.
- **Steps (API):**
  4. With balance €25.50, call `POST /api/place-bet` with `stake` 50 directly.

- **Expected result:**
  - UI blocks placement and shows an "Insufficient balance" message (Spec §4.4).
  - API rejects with a `422` semantic validation error and does not change the balance
    (Spec §4.1 — "Show/reject as insufficient balance").
  - `GET /api/balance` after the attempt is unchanged.

---

## TC-03 — Stake boundary values at the min/max limits (UI and API)

- **Priority:** High
- **Type:** Boundary
- **Risk rationale:** The limits €1.00 and €100.00 are the edges where off-by-one errors live, and
  the specification is internally **contradictory** on the minimum (Business Rules and the UI copy
  say €1.00; the validation table §4.1 says €1.01). The API schema defines `minimum: 1`, so €1.00
  is treated as the correct, bettable boundary. Pinning these edges protects a regulated limit and
  surfaces the spec conflict.

- **Preconditions:** Balance reset to €125.50.

- **Steps:** Attempt placement (UI and API) for each stake:
  `0.99`, `1.00`, `1.01`, `100.00`, `100.01`.

- **Expected result:**
  - `0.99` → rejected, "Minimum stake is €1.00" (Spec §4.4).
  - `1.00` → **accepted** (API schema `minimum: 1`; Business Rules; UI copy).
  - `1.01` → accepted.
  - `100.00` → accepted.
  - `100.01` → rejected, "Maximum stake is €100.00" (Spec §4.4).
  - API returns `422` for the rejected values; balance changes only for accepted bets.
  - *Note:* the §4.1 "€1.01" minimum is treated as a specification error, not an app requirement.

---

## TC-04 — Bet failure path: error modal, Rebet, and Close behaviour

- **Priority:** High
- **Type:** Negative / state handling
- **Risk rationale:** When placement fails, the retry (**Rebet**) must not double-charge, and
  **Close**/**X** must leave the app in a clean state. A retry that charges twice, or a first
  attempt that silently deducts before showing an error, is a direct financial loss. This covers
  the "resolve to one final outcome" and error-modal rules (Spec §2.3, §2.5).

- **Preconditions:** A way to trigger the failure path (if the failure is non-deterministic, this
  is noted as a limitation and the check is exploratory).

- **Steps:**
  1. Trigger a bet that resolves to the error modal.
  2. Verify modal title and body copy.
  3. Note the balance (via `GET /api/balance`) while the error modal is open.
  4. Click **Rebet**; observe whether placement is retried.
  5. In a fresh failed attempt, click **Close** (and separately the top-right **X**).

- **Expected result:**
  - Error modal titled "Something went wrong" with a retry suggestion (Spec §2.5).
  - Only one final outcome is shown — never a receipt and an error together (Spec §2.3).
  - Balance is **not** deducted by a failed attempt.
  - **Rebet** retries placement once and does not produce a second deduction.
  - **Close** and **X** both close the modal and clear the current selection/stake (Spec §2.5).

---

## TC-05 — Stake input format and precision validation (UI and API)

- **Priority:** Medium
- **Type:** Negative / validation / boundary
- **Risk rationale:** Stake is free user input and directly sets the amount of money at stake.
  Non-numeric, negative, zero, over-precise, or wrongly separated values must be rejected
  consistently so no malformed amount reaches the ledger (Spec §4.1, §4.4). Lower priority than
  TC-01–TC-03 because the impact per case is smaller, but it rounds out input integrity.

- **Preconditions:** Balance reset to €125.50.

- **Steps:** Attempt placement for: `abc` (non-numeric), empty stake, `-5` (negative), `0`,
  `10.555` (3 decimals), `10,50` (comma separator).

- **Expected result:**
  - Non-numeric and empty → placement blocked/rejected (Spec §4.1 — required, numeric).
  - `-5` and `0` → rejected as below the €1.00 positive minimum.
  - `10.555` → rejected for precision (max 2 decimal places, Spec §4.1).
  - Comma separator → handled per the single-decimal-separator rule (Spec §4.4); behaviour for
    comma vs dot is confirmed and recorded, as the spec does not state which separator is required.
  - API returns `400`/`422` as appropriate and never `500`; balance unchanged for all rejects.

---

## TC-06 — API contract and request validation for `place-bet`

- **Priority:** High
- **Type:** Negative / contract
- **Risk rationale:** The API is the second gate and is reachable without the UI. Selection enum,
  match existence, payload shape, auth context, and method handling must all be enforced server-side
  (Spec §4.2, §4.3, §5). Weakness here means the UI's protections can be bypassed entirely.

- **Preconditions:** Valid and invalid `user-id` values available.

- **Steps / cases:**
  1. `selection` not in `HOME|DRAW|AWAY` (e.g. `"home"`, `"BANANA"`).
  2. Missing `selection`; missing `matchId`.
  3. Unknown `matchId`.
  4. Malformed JSON body; a JSON array instead of an object.
  5. Missing / empty `x-user-id`.
  6. Unsupported method (`GET /api/place-bet`).
  7. Extra fields in body (e.g. `odds`, `payout`) — must be ignored.

- **Expected result:**
  - Invalid/missing selection or match → `422` (Spec §4.2).
  - Malformed or non-object body → `400` (Spec §4.3).
  - Missing/invalid user context → `401` (Spec §4.3, §5.1).
  - Unsupported method → `405` (Spec §4.3).
  - Extra fields are ignored and do not affect the computed odds/payout (Spec §5.3).

---

## Priority summary

| ID | Title | Priority | Type |
|---|---|---|---|
| TC-01 | Valid bet; balance and receipt verified | Critical | Happy path |
| TC-02 | Stake exceeding balance rejected (UI+API) | Critical | Negative |
| TC-03 | Stake min/max boundary values | High | Boundary |
| TC-04 | Failure path: error modal, Rebet, Close | High | Negative / state |
| TC-05 | Stake input format and precision | Medium | Negative / boundary |
| TC-06 | API contract and request validation | High | Negative / contract |

**Top 3 selected for execution:** TC-01, TC-02, TC-03 — the three with the greatest financial
risk and the clearest, most deterministic checks.

**Intentionally lower priority / out of this set:** date and odds **filters** (Spec §2.6). They do
not touch money, the spec leaves their edge rules ambiguous, and their failure degrades convenience
rather than funds — so they are better suited to exploratory/manual testing than to the prioritized
core set.
