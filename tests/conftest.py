import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest

from app import app as flask_app
from database import db as db_module


@pytest.fixture
def app(tmp_path, monkeypatch):
    test_db_path = tmp_path / "test_expense_tracker.db"
    monkeypatch.setattr(db_module, "DB_PATH", str(test_db_path))
    flask_app.config.update(TESTING=True)
    with flask_app.app_context():
        db_module.init_db()
        db_module.seed_db()
    yield flask_app
