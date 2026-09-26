from database import db as db_module

SEED_TOTAL = 426.64
SEED_COUNT = 8
SEED_TOP_CATEGORY = "Bills"
SEED_CATEGORY_COUNT = 7


def _seed_user_id():
    user = db_module.get_user_by_email("demo@spendly.com")
    return user["id"]


def _fresh_user_id():
    return db_module.create_user("New User", "new@example.com", "password123")


# ---------------------------------------------------------------- #
# get_user_by_id
# ---------------------------------------------------------------- #

def test_get_user_by_id_valid(app):
    user = db_module.get_user_by_id(_seed_user_id())
    assert user["name"] == "Demo User"
    assert user["email"] == "demo@spendly.com"
    assert isinstance(user["member_since"], str) and len(user["member_since"].split()) == 2


def test_get_user_by_id_missing(app):
    assert db_module.get_user_by_id(999999) is None


# ---------------------------------------------------------------- #
# get_summary_stats
# ---------------------------------------------------------------- #

def test_get_summary_stats_with_expenses(app):
    stats = db_module.get_summary_stats(_seed_user_id())
    assert round(stats["total_spent"], 2) == SEED_TOTAL
    assert stats["transaction_count"] == SEED_COUNT
    assert stats["top_category"] == SEED_TOP_CATEGORY


def test_get_summary_stats_no_expenses(app):
    stats = db_module.get_summary_stats(_fresh_user_id())
    assert stats == {"total_spent": 0, "transaction_count": 0, "top_category": "—"}


# ---------------------------------------------------------------- #
# get_recent_transactions
# ---------------------------------------------------------------- #

def test_get_recent_transactions_with_expenses(app):
    transactions = db_module.get_recent_transactions(_seed_user_id())
    assert len(transactions) == SEED_COUNT
    dates = [tx["date"] for tx in transactions]
    assert dates == sorted(dates, reverse=True)
    for tx in transactions:
        assert set(tx.keys()) == {"date", "description", "category", "amount"}


def test_get_recent_transactions_no_expenses(app):
    assert db_module.get_recent_transactions(_fresh_user_id()) == []


# ---------------------------------------------------------------- #
# get_category_breakdown
# ---------------------------------------------------------------- #

def test_get_category_breakdown_with_expenses(app):
    breakdown = db_module.get_category_breakdown(_seed_user_id())
    assert len(breakdown) == SEED_CATEGORY_COUNT
    amounts = [c["amount"] for c in breakdown]
    assert amounts == sorted(amounts, reverse=True)
    assert sum(c["pct"] for c in breakdown) == 100
    assert all(isinstance(c["pct"], int) for c in breakdown)


def test_get_category_breakdown_no_expenses(app):
    assert db_module.get_category_breakdown(_fresh_user_id()) == []


# ---------------------------------------------------------------- #
# GET /profile
# ---------------------------------------------------------------- #

def test_profile_redirects_when_unauthenticated(client):
    response = client.get("/profile")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_profile_authenticated(client):
    with client.session_transaction() as sess:
        sess["user_id"] = _seed_user_id()

    response = client.get("/profile")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Demo User" in body
    assert "demo@spendly.com" in body
    assert "₹" in body
    assert "426.64" in body
    assert "Bills" in body
    assert body.count("<tr>") - 1 == SEED_COUNT  # subtract the header row


def test_profile_new_user_has_empty_state(client):
    with client.session_transaction() as sess:
        sess["user_id"] = _fresh_user_id()

    response = client.get("/profile")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "₹0.00" in body
    assert "No transactions yet." in body
    assert "No expenses yet." in body
