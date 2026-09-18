# Spec: Profile Page Design

## Overview
This step implements the `GET /profile` route, currently a stub (`return "Profile page — coming in Step 4"`) with no template and no auth check. Step 3 (login/logout) already redirects a successful login to `url_for('profile')` and its spec explicitly calls `/profile` "the prerequisite for any session-protected page" — so this is the first route in the app that requires an authenticated session. This step makes `/profile` a real, logged-in-only page that displays the current user's account info (name, email, member-since date) and a simple summary of their expense activity (total spent, number of expenses), all derived from data that already exists in the schema. Editing profile fields is explicitly out of scope for this step — display only.

## Depends on
- Step 1 (Database Setup) — `users` and `expenses` tables, `get_db()`
- Step 2 (Registration) — `users` rows with `name`, `email`, `created_at`
- Step 3 (Login/Logout) — `session["user_id"]` set on login, cleared on logout

## Routes
- `GET /profile` — renders the logged-in user's profile (name, email, member-since date, total expenses count, total amount spent) — logged-in only. If `session.get("user_id")` is missing, redirect to `url_for('login')`.

No other new routes.

## Database changes
No new tables or columns. `users` (id, name, email, password_hash, created_at) and `expenses` (id, user_id, amount, category, date, description, created_at) already carry everything this step needs.

New helper functions in `database/db.py` (no inline SQL in `app.py`):
- `get_user_by_id(user_id)` — `SELECT id, name, email, created_at FROM users WHERE id = ?`, parameterized, returns one row or `None`.
- `get_expense_summary(user_id)` — `SELECT COUNT(*) AS count, COALESCE(SUM(amount), 0) AS total FROM expenses WHERE user_id = ?`, parameterized, returns one row.

## Templates
- **Create:** `templates/profile.html` — extends `base.html`; overrides `title` and `content`; displays name, email, "member since" (formatted from `created_at`), and the expense summary (count + total). Reuses existing card/component classes (`.feature-card`, `.auth-card`-style patterns) where they fit rather than inventing new ones unnecessarily.
- **Modify:** `templates/base.html` — the nav is currently static and always shows "Sign in" / "Get started", with no session awareness. Add a `{% if session.user_id %}` branch: when logged in, show links to `Profile` (`url_for('profile')`) and `Logout` (`url_for('logout')`); when logged out, keep the existing "Sign in" / "Get started" links.

## Files to change
- `app.py` — implement `GET /profile`: check `session.get("user_id")`, redirect to `login` if absent, otherwise fetch user + expense summary via the new `db.py` helpers and render `profile.html`.
- `database/db.py` — add `get_user_by_id()` and `get_expense_summary()`.
- `templates/base.html` — session-aware nav (Profile/Logout vs. Sign in/Get started).

## Files to create
- `templates/profile.html`
- `static/css/profile.css` — page-specific styles for the profile layout (e.g. summary cards), loaded via `{% block head %}` in `profile.html`, following the same pattern `landing.html` uses for `landing.css`. Only add rules here that don't already exist in `style.css`.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug (n/a for this step — no password handling here)
- Use CSS variables — never hardcode hex values (reuse the existing `--ink`, `--paper`, `--accent`, etc. tokens from `style.css`)
- All templates extend `base.html`
- No DB logic inline in `app.py` — all queries live in `database/db.py`
- Use `abort()`/redirect via `url_for()` for the auth guard — never hardcode `/login` as a string
- Do not add profile editing, avatar upload, or any new `users` columns — display only, per this step's scope

## Definition of done
- [ ] Visiting `/profile` while logged out redirects to `/login`
- [ ] Logging in as the seeded demo user (`demo@spendly.com` / `demo123`) redirects to `/profile` and renders the page (no raw string, no traceback)
- [ ] Profile page shows the correct name, email, and a "member since" date for the logged-in user
- [ ] Profile page shows the correct total expense count and total amount spent, matching the 8 seeded demo expenses
- [ ] Nav bar shows "Profile" and "Logout" when logged in, and "Sign in"/"Get started" when logged out, on every page that extends `base.html`
- [ ] Clicking "Logout" from the profile page clears the session and redirects to the landing page, and `/profile` redirects to `/login` again afterward
- [ ] No hardcoded URLs in `profile.html` or the modified nav — all links use `url_for()`
- [ ] No hardcoded hex colors in `profile.css` — only existing CSS variables from `style.css`
