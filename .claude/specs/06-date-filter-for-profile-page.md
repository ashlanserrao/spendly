# Spec: Date Filter for Profile Page

## Overview
Step 6 adds a date-range filter to the profile page. A logged-in user can pick a
start date and/or end date and the summary stats, transaction list, and category
breakdown all recompute for expenses within that range. With no filter applied
the page behaves exactly as it does after Step 5 (all-time data). This builds on
the live-data profile from Step 5 and gives users a way to answer "how much did
I spend this month?" before the add/edit/delete expense steps arrive.

## Depends on
- Step 1: Database setup (`get_db()`, `expenses` table)
- Step 3: Login / Logout (`session["user_id"]`)
- Step 4: Profile page UI (`profile.html`, `profile.css`)
- Step 5: Backend routes for profile (`get_summary_stats`, `get_recent_transactions`, `get_category_breakdown` in `database/db.py`)

## Routes
No new routes. The existing `GET /profile` accepts two optional query-string
parameters — logged-in only:
- `start_date` — `YYYY-MM-DD`, inclusive lower bound
- `end_date` — `YYYY-MM-DD`, inclusive upper bound

Either, both, or neither may be supplied. The filter form submits via `GET` so
filtered views are bookmarkable. A "Clear" link returns to plain `/profile`.

## Database changes
No database changes. `expenses.date` is stored as ISO `YYYY-MM-DD` text, so
string comparison (`date >= ?` / `date <= ?`) is correct and no index or column
is needed.

## Templates
- **Create:** none
- **Modify:** `templates/profile.html`
  - Add a filter form (two `<input type="date">` fields, an "Apply" button, a "Clear" link built with `url_for('profile')`) above the summary stats. Inputs are pre-filled with the currently active `start_date` / `end_date`.
  - Show an error message inside the filter card when the range is invalid.
  - Empty-state text for the transaction list and category breakdown should read "No expenses in this date range." when a filter is active, otherwise keep the current text.
  - Form `action` must use `url_for('profile')`.

## Files to change
- `app.py` — `profile()` reads and validates `start_date` / `end_date`, passes them to the query helpers, and passes the active values and any error to the template
- `database/db.py` — add optional `start_date=None, end_date=None` parameters to `get_summary_stats`, `get_recent_transactions`, and `get_category_breakdown`
- `templates/profile.html` — filter form, error display, filtered empty states
- `static/css/profile.css` — styles for the filter form (page-specific styles stay in this file)
- `CLAUDE.md` — no change expected (`/profile` is already implemented)

## Files to create
- `tests/test_date_filter.py` — written via the `/test-feature` workflow, not by hand

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only — build the optional `AND date >= ?` / `AND date <= ?` clauses from fixed string fragments and append values to the params tuple; never interpolate user input into SQL
- Passwords hashed with werkzeug (unchanged; no auth changes in this step)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- DB logic stays in `database/db.py`; the route only parses input, calls helpers, and renders
- Validate dates in the route with `datetime.strptime(value, "%Y-%m-%d")`; blank values mean "no bound"
- Invalid input (unparseable date, or `start_date` later than `end_date`) must not raise: show an error message and fall back to the unfiltered data
- Existing helper calls with no date arguments must keep returning identical results (backward compatible defaults)
- The summary stats, transaction list, and category breakdown must all use the same range so the page is internally consistent
- `get_recent_transactions` keeps its default `limit=10`; the filter does not change that
- Category `pct` values must still sum to 100 within the filtered set; empty filtered set returns zeros / empty list, never an exception
- Currency continues to display as ₹
- No inline `<style>` tags; do not add new inline `style=` attributes
- Do not implement any other stub route

## Definition of done
- [ ] `/profile` with no query string looks and behaves exactly as before (₹426.64 total, 8 transactions for the seed user)
- [ ] The profile page shows a filter form with start and end date inputs, an Apply button, and a Clear link
- [ ] Submitting a range narrows the total spent, expense count, top category, transaction list, and category breakdown to expenses with dates inside the range (both ends inclusive)
- [ ] Supplying only `start_date` filters from that date onward; supplying only `end_date` filters up to that date
- [ ] After applying a filter, the date inputs remain pre-filled with the chosen values
- [ ] Clicking Clear returns to `/profile` with all-time data and empty inputs
- [ ] A range containing no expenses shows ₹0.00, 0 expenses, "—" as top category, and the "No expenses in this date range." message — no errors
- [ ] Category percentages in a filtered view sum to 100
- [ ] `/profile?start_date=2026-12-31&end_date=2026-01-01` shows an error message and falls back to all-time data
- [ ] `/profile?start_date=not-a-date` shows an error message and does not return a 500
- [ ] A SQL-injection-style value such as `start_date=' OR 1=1 --` is rejected by validation and does not alter results
- [ ] Unauthenticated access to `/profile?start_date=2026-01-01` still redirects to `/login`
- [ ] A user only ever sees their own expenses under any filter
