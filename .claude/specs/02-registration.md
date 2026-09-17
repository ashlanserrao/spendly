# Spec: Registration

## Overview
This step wires up account creation for Spendly. `GET /register` already renders `register.html` with a form posting to `/register`, but nothing currently handles that submission. This spec implements `POST /register` so a visitor can submit their name, email, and password, have the password hashed, and have a new row created in the `users` table — turning the existing static form into a working signup flow. This is the first piece of the authentication system; login/session handling is out of scope and will follow in a later step.

## Depends on
- Step 1 (database setup) — requires `database/db.py`'s `users` table, `get_db()` connection helper, and the `UNIQUE` constraint on `email` to already exist.

## Routes
- `POST /register` — reads `name`, `email`, `password` from the submitted form, validates them, hashes the password, inserts a new user, then redirects to `GET /login` on success (or re-renders `register.html` with an `error` message on failure) — public

## Database changes
No database changes. The existing `users` table (`id`, `name`, `email` UNIQUE, `password_hash`, `created_at`) already supports this feature as defined in `database/db.py`.

## Templates
- **Create:** none
- **Modify:** `templates/register.html` — no structural changes needed; it already reads `{{ error }}` via the existing `auth-error` block, so validation/duplicate-email failures render through the current markup.

## Files to change
- `app.py` — add the `POST` method to the `/register` route (or a matching `methods=["POST"]` handler), calling into `database/db.py` for validation/insert logic, and rendering `register.html` with an `error` on failure or redirecting to `url_for('login')` on success.
- `database/db.py` — add the DB-logic helpers needed to support registration (e.g. a lookup by email and a user-insert helper), since route functions must not contain inline SQL.

## Files to create
None.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug (`generate_password_hash`)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- No DB logic inline in `app.py` routes — it belongs in `database/db.py`
- Never hardcode URLs in templates — always use `url_for()`
- Use `abort()` for HTTP errors, not bare `return "error string"`
- Duplicate email must be rejected with a user-facing error, not a raw `sqlite3.IntegrityError`

## Definition of done
- [ ] Submitting the register form with valid, unique details creates a new row in `users` with a hashed (not plaintext) password
- [ ] After a successful registration, the browser is redirected to `/login`
- [ ] Submitting an already-registered email re-renders `register.html` with a visible error and does not create a duplicate row
- [ ] Submitting with a missing field (name/email/password) re-renders `register.html` with a visible error and does not insert a row
- [ ] `python app.py` starts without errors and `/register` still responds to `GET` as before
- [ ] All new SQL in `database/db.py` uses `?` parameterized placeholders
