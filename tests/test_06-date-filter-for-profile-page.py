"""Tests for Step 6: date-range filter on GET /profile (see spec 06)."""
from datetime import date

import pytest

from database import db as db_module

SEED_TOTAL = "426.64"
SEED_COUNT = 8

# Fixed-date dataset for a dedicated user (deterministic, independent of today).
FIXED_ROWS = [
    (100.00, "Food", "2020-01-10", "jan food"),
    (50.00, "Bills", "2020-01-20", "jan bills"),
    (25.00, "Food", "2020-02-05", "feb food"),
    (25.00, "Travel", "2020-03-01", "mar travel"),
]
FIXED_TOTAL = "200.00"


@pytest.fixture
def client(app):
    return app.test_client()


def _login(client, user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id


def _insert_expenses(user_id, rows):
    conn = db_module.get_db()
    try:
        conn.executemany(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            [(user_id, a, c, d, desc) for a, c, d, desc in rows],
        )
        conn.commit()
    finally:
        conn.close()


@pytest.fixture
def fixed_user(app):
    uid = db_module.create_user("Fixed User", "fixed@example.com", "password123")
    _insert_expenses(uid, FIXED_ROWS)
    return uid


@pytest.fixture
def fixed_client(client, fixed_user):
    _login(client, fixed_user)
    return client


@pytest.fixture
def seed_client(client, app):
    _login(client, db_module.get_user_by_email("demo@spendly.com")["id"])
    return client


def _get(client, **params):
    resp = client.get("/profile", query_string=params)
    return resp, resp.get_data(as_text=True)


def _row_count(body):
    return body.count("<tr>") - 1  # minus header row


ERROR_WORDS = ("invalid", "error", "must be", "not a valid", "before")


def _has_error(body):
    low = body.lower()
    return any(w in low for w in ERROR_WORDS)


# ---------------------------------------------------------------- #
# Auth guard
# ---------------------------------------------------------------- #

class TestAuthGuard:
    @pytest.mark.parametrize("qs", [
        "?start_date=2026-01-01",
        "?end_date=2026-12-31",
        "?start_date=2026-01-01&end_date=2026-12-31",
        "?start_date=garbage",
    ])
    def test_unauthenticated_filtered_profile_redirects_to_login(self, client, qs):
        response = client.get("/profile" + qs)
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]


# ---------------------------------------------------------------- #
# No filter / backward compatibility
# ---------------------------------------------------------------- #

class TestUnfiltered:
    def test_no_query_string_shows_all_time_seed_data(self, seed_client):
        resp, body = _get(seed_client)
        assert resp.status_code == 200
        assert SEED_TOTAL in body
        assert _row_count(body) == SEED_COUNT

    def test_blank_dates_mean_no_bounds(self, seed_client):
        resp, body = _get(seed_client, start_date="", end_date="")
        assert resp.status_code == 200
        assert SEED_TOTAL in body
        assert _row_count(body) == SEED_COUNT
        assert not _has_error(body)

    def test_new_user_unfiltered_empty_states_preserved(self, client, app):
        uid = db_module.create_user("New", "new@example.com", "password123")
        _login(client, uid)
        resp, body = _get(client)
        assert resp.status_code == 200
        assert "No transactions yet." in body
        assert "No expenses yet." in body
        assert "No expenses in this date range." not in body

    def test_helpers_without_dates_are_backward_compatible(self, app):
        uid = db_module.get_user_by_email("demo@spendly.com")["id"]
        stats = db_module.get_summary_stats(uid)
        assert round(stats["total_spent"], 2) == float(SEED_TOTAL)
        assert stats["transaction_count"] == SEED_COUNT
        assert len(db_module.get_recent_transactions(uid)) == SEED_COUNT
        assert sum(c["pct"] for c in db_module.get_category_breakdown(uid)) == 100


# ---------------------------------------------------------------- #
# Filter form UI
# ---------------------------------------------------------------- #

class TestFilterForm:
    def test_form_has_date_inputs_apply_and_clear(self, seed_client):
        _, body = _get(seed_client)
        assert body.count('type="date"') >= 2, "Expected two date inputs"
        assert 'name="start_date"' in body
        assert 'name="end_date"' in body
        assert "Apply" in body
        assert "Clear" in body

    def test_form_submits_via_get_to_profile(self, seed_client):
        _, body = _get(seed_client)
        assert 'method="get"' in body.lower()
        assert 'action="/profile"' in body

    def test_clear_link_points_to_plain_profile(self, seed_client):
        _, body = _get(seed_client)
        assert 'href="/profile"' in body

    def test_inputs_prefilled_after_filtering(self, fixed_client):
        _, body = _get(fixed_client, start_date="2020-01-10", end_date="2020-02-05")
        assert 'value="2020-01-10"' in body
        assert 'value="2020-02-05"' in body

    def test_inputs_empty_without_filter(self, fixed_client):
        _, body = _get(fixed_client)
        assert 'value="2020-' not in body


# ---------------------------------------------------------------- #
# Filtering behaviour
# ---------------------------------------------------------------- #

class TestFiltering:
    def test_both_bounds_are_inclusive(self, fixed_client):
        resp, body = _get(fixed_client, start_date="2020-01-10", end_date="2020-01-20")
        assert resp.status_code == 200
        assert "150.00" in body
        assert _row_count(body) == 2
        assert "jan food" in body and "jan bills" in body
        assert "feb food" not in body and "mar travel" not in body

    def test_single_day_range(self, fixed_client):
        resp, body = _get(fixed_client, start_date="2020-02-05", end_date="2020-02-05")
        assert "feb food" in body
        assert _row_count(body) == 1
        assert "25.00" in body

    def test_only_start_date_filters_from_date_onward(self, fixed_client):
        resp, body = _get(fixed_client, start_date="2020-02-01")
        assert _row_count(body) == 2
        assert "feb food" in body and "mar travel" in body
        assert "jan food" not in body
        assert "50.00" in body

    def test_only_end_date_filters_up_to_date(self, fixed_client):
        resp, body = _get(fixed_client, end_date="2020-01-31")
        assert _row_count(body) == 2
        assert "jan food" in body and "jan bills" in body
        assert "feb food" not in body
        assert "150.00" in body

    def test_full_range_equals_all_time(self, fixed_client):
        resp, body = _get(fixed_client, start_date="2020-01-01", end_date="2020-12-31")
        assert FIXED_TOTAL in body
        assert _row_count(body) == len(FIXED_ROWS)

    def test_top_category_reflects_filter(self, fixed_client):
        # Unfiltered top is Food (125); restricted to Jan 20 only, Bills is the top.
        _, body = _get(fixed_client, start_date="2020-01-20", end_date="2020-01-20")
        assert "Bills" in body
        assert "jan food" not in body

    def test_category_breakdown_limited_to_range(self, fixed_client):
        _, body = _get(fixed_client, start_date="2020-03-01", end_date="2020-03-31")
        assert "Travel" in body
        assert "Bills" not in body

    def test_seed_user_current_month_filter(self, seed_client):
        today = date.today()
        start = today.replace(day=1).isoformat()
        end = today.replace(day=9).isoformat()
        resp, body = _get(seed_client, start_date=start, end_date=end)
        assert resp.status_code == 200
        # Seed days 2, 4, 5, 9 fall in the range.
        assert _row_count(body) == 4
        assert SEED_TOTAL not in body

    def test_filter_in_future_has_no_results(self, seed_client):
        resp, body = _get(seed_client, start_date="2999-01-01")
        assert resp.status_code == 200
        assert "No expenses in this date range." in body
        assert "₹0.00" in body


# ---------------------------------------------------------------- #
# Empty filtered result
# ---------------------------------------------------------------- #

class TestEmptyRange:
    def test_empty_range_shows_zero_stats_and_message(self, fixed_client):
        resp, body = _get(fixed_client, start_date="2019-01-01", end_date="2019-12-31")
        assert resp.status_code == 200
        assert "₹0.00" in body
        assert "—" in body
        assert "No expenses in this date range." in body
        assert "No transactions yet." not in body
        assert "No expenses yet." not in body
        assert not _has_error(body) or "No expenses in this date range." in body

    def test_helpers_return_empty_values_for_empty_range(self, fixed_user):
        stats = db_module.get_summary_stats(
            fixed_user, start_date="2019-01-01", end_date="2019-12-31")
        assert stats == {"total_spent": 0, "transaction_count": 0, "top_category": "—"}
        assert db_module.get_recent_transactions(
            fixed_user, start_date="2019-01-01", end_date="2019-12-31") == []
        assert db_module.get_category_breakdown(
            fixed_user, start_date="2019-01-01", end_date="2019-12-31") == []


# ---------------------------------------------------------------- #
# DB helper behaviour with date args
# ---------------------------------------------------------------- #

class TestHelpers:
    def test_summary_stats_filtered(self, fixed_user):
        stats = db_module.get_summary_stats(
            fixed_user, start_date="2020-01-01", end_date="2020-01-31")
        assert round(stats["total_spent"], 2) == 150.00
        assert stats["transaction_count"] == 2
        assert stats["top_category"] == "Food"

    def test_summary_stats_only_start(self, fixed_user):
        stats = db_module.get_summary_stats(fixed_user, start_date="2020-02-05")
        assert stats["transaction_count"] == 2
        assert round(stats["total_spent"], 2) == 50.00

    def test_summary_stats_only_end(self, fixed_user):
        stats = db_module.get_summary_stats(fixed_user, end_date="2020-01-10")
        assert stats["transaction_count"] == 1
        assert round(stats["total_spent"], 2) == 100.00

    def test_recent_transactions_filtered_and_ordered(self, fixed_user):
        txs = db_module.get_recent_transactions(
            fixed_user, start_date="2020-01-15", end_date="2020-03-01")
        dates = [t["date"] for t in txs]
        assert dates == ["2020-03-01", "2020-02-05", "2020-01-20"]

    def test_recent_transactions_limit_still_applies(self, app):
        uid = db_module.create_user("Many", "many@example.com", "password123")
        _insert_expenses(uid, [(1.0, "Food", f"2020-05-{d:02d}", f"d{d}") for d in range(1, 16)])
        txs = db_module.get_recent_transactions(
            uid, start_date="2020-05-01", end_date="2020-05-31")
        assert len(txs) == 10
        assert db_module.get_summary_stats(
            uid, start_date="2020-05-01", end_date="2020-05-31")["transaction_count"] == 15

    @pytest.mark.parametrize("start,end", [
        ("2020-01-01", "2020-12-31"),
        ("2020-01-01", "2020-01-31"),
        ("2020-02-01", None),
        (None, "2020-02-28"),
    ])
    def test_category_pct_sums_to_100(self, fixed_user, start, end):
        breakdown = db_module.get_category_breakdown(
            fixed_user, start_date=start, end_date=end)
        assert breakdown
        assert sum(c["pct"] for c in breakdown) == 100

    def test_category_breakdown_filtered_categories(self, fixed_user):
        breakdown = db_module.get_category_breakdown(
            fixed_user, start_date="2020-02-01", end_date="2020-03-31")
        assert len(breakdown) == 2
        assert sum(c["amount"] for c in breakdown) == pytest.approx(50.00)


# ---------------------------------------------------------------- #
# Validation errors
# ---------------------------------------------------------------- #

class TestInvalidInput:
    def test_start_after_end_shows_error_and_all_time_data(self, fixed_client):
        _, baseline = _get(fixed_client)
        resp, body = _get(fixed_client, start_date="2020-12-31", end_date="2020-01-01")
        assert resp.status_code == 200
        assert _has_error(body) and not _has_error(baseline), "Expected an error message"
        assert FIXED_TOTAL in body
        assert _row_count(body) == len(FIXED_ROWS)

    @pytest.mark.parametrize("params", [
        {"start_date": "not-a-date"},
        {"end_date": "not-a-date"},
        {"start_date": "2020-13-45"},
        {"start_date": "2020-02-30"},
        {"start_date": "01/02/2020"},
        {"start_date": "2020-01-01", "end_date": "garbage"},
    ])
    def test_unparseable_date_shows_error_without_500(self, fixed_client, params):
        _, baseline = _get(fixed_client)
        resp, body = _get(fixed_client, **params)
        assert resp.status_code == 200
        assert _has_error(body) and not _has_error(baseline), "Expected an error message"
        assert FIXED_TOTAL in body
        assert _row_count(body) == len(FIXED_ROWS)

    @pytest.mark.parametrize("payload", [
        "' OR 1=1 --",
        "2020-01-01'; DROP TABLE expenses; --",
        "\" OR \"1\"=\"1",
    ])
    def test_sql_injection_value_rejected_and_results_unchanged(self, fixed_client, payload):
        resp, body = _get(fixed_client, start_date=payload)
        assert resp.status_code == 200
        assert _row_count(body) == len(FIXED_ROWS)
        assert FIXED_TOTAL in body
        # Table must still exist and be intact.
        conn = db_module.get_db()
        try:
            n = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
        finally:
            conn.close()
        assert n >= len(FIXED_ROWS)

    def test_sql_injection_in_end_date_does_not_500(self, fixed_client):
        resp, body = _get(fixed_client, end_date="' OR 1=1 --")
        assert resp.status_code == 200
        assert _row_count(body) == len(FIXED_ROWS)

    def test_very_long_value_does_not_500(self, fixed_client):
        resp, _ = _get(fixed_client, start_date="9" * 5000)
        assert resp.status_code == 200

    def test_filter_does_not_modify_database(self, fixed_client):
        _get(fixed_client, start_date="2020-01-01", end_date="2020-01-31")
        conn = db_module.get_db()
        try:
            n = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
        finally:
            conn.close()
        assert n == SEED_COUNT + len(FIXED_ROWS)


# ---------------------------------------------------------------- #
# User isolation
# ---------------------------------------------------------------- #

class TestUserIsolation:
    def test_filter_only_shows_own_expenses(self, client, fixed_user):
        other = db_module.create_user("Other", "other@example.com", "password123")
        _insert_expenses(other, [(999.0, "Shopping", "2020-01-15", "other secret")])

        _login(client, fixed_user)
        _, body = _get(client, start_date="2020-01-01", end_date="2020-01-31")
        assert "other secret" not in body
        assert "999.00" not in body
        assert "150.00" in body

        _login(client, other)
        _, body = _get(client, start_date="2020-01-01", end_date="2020-01-31")
        assert "other secret" in body
        assert "jan food" not in body
        assert _row_count(body) == 1

    def test_helpers_scope_by_user_under_filter(self, fixed_user):
        other = db_module.create_user("Other", "other2@example.com", "password123")
        _insert_expenses(other, [(500.0, "Shopping", "2020-01-15", "x")])
        stats = db_module.get_summary_stats(
            fixed_user, start_date="2020-01-01", end_date="2020-01-31")
        assert round(stats["total_spent"], 2) == 150.00
        txs = db_module.get_recent_transactions(
            fixed_user, start_date="2020-01-01", end_date="2020-01-31")
        assert all(t["description"] != "x" for t in txs)
