# Spec: Login and Logout

## Overview
This step completes the authentication loop started by registration (Step 2). `GET /login` already renders `login.html` with a working form, but nothing handles its submission, and there is no session mechanism anywhere in the app yet. This spec implements `POST /login` (verify credentials, start a session) and a working `GET /logout` (end the session), replacing the current logout stub. Together these let a registered user actually sign in and sign out — the prerequisite for any session-protected page, including the `/profile` stub that follows in Step 4.

## Depends on
- Step 1 (database setup) — `users` table, `get_db()`.
- Step 2 (registration) — a user must exist (via `POST /register` or the seeded demo user) before they can log in; reuses the `get_user_by_email` pattern established in `database/db.py`.

## Routes
- `POST /login` — reads `email`, `password` from the submitted form, looks up the user, verifies the password against the stored hash, and on success stores the user's id in the session and redirects to `GET /profile`. On failure (unknown email or wrong password), re-renders `login.html` with a single generic error — public
- `GET /logout` — clears the session (if any) and redirects to `GET /` (landing). Replaces the current stub, which returns a bare string in violation of the "never use raw string returns for stub routes once implemented" rule — logged-in (safe to hit while logged out too; it simply becomes a no-op redirect)

## Database changes
No database changes. The existing `users` table (`id`, `name`, `email` UNIQUE, `password_hash`, `created_at`) already has everything needed to verify a login.

## Templates
- **Create:** none
- **Modify:** none — `templates/login.html` already posts to `/login` with fields `email`/`password` and reads `{{ error }}` via the existing `auth-error` block, matching the pattern used by `register.html` in Step 2.

## Files to change
- `app.py` —
  - Set `app.secret_key` (required for Flask's signed session cookie; nothing in this codebase sets one yet). No existing env-var convention exists in this project, so a fixed development key defined directly in `app.py` is acceptable.
  - Add `POST` handling to `/login`, calling into `database/db.py` for credential verification, setting `session["user_id"]` on success, and redirecting to `url_for('profile')`.
  - Replace the `/logout` stub with a real implementation: clear the session and redirect to `url_for('landing')`.
- `database/db.py` — add a credential-verification helper (e.g. `verify_user(email, password)`) that fetches the user by email and checks the password with `werkzeug.security.check_password_hash`, mirroring how `create_user` already owns hashing on the registration side.

## Files to create
None.

## New dependencies
No new dependencies. Flask's built-in `session` (signed cookies) requires no new package; `werkzeug.security.check_password_hash` ships alongside the already-used `generate_password_hash`.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug (verification via `check_password_hash`, matching hashing done during registration)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- No DB logic inline in `app.py` routes — it belongs in `database/db.py`
- Never hardcode URLs in templates — always use `url_for()`
- Use `abort()` for HTTP errors, not bare `return "error string"` (this retires the current `/logout` stub's raw string return)
- Use one generic error message for both "unknown email" and "wrong password" so the login form never reveals whether a given email is registered

## Definition of done
- [ ] Logging in with the seeded demo account (`demo@spendly.com` / `demo123`) redirects to `/profile` and a session cookie is set
- [ ] Logging in with a correct email but wrong password re-renders `login.html` with a visible, generic error and no session is set
- [ ] Logging in with an email that doesn't exist re-renders `login.html` with the same generic error and no session is set
- [ ] Visiting `/logout` while logged in clears the session and redirects to `/`
- [ ] Visiting `/logout` while not logged in does not error — it still redirects to `/`
- [ ] `python app.py` starts without errors and `GET /login` still renders the form as before
- [ ] All new SQL in `database/db.py` uses `?` parameterized placeholders
