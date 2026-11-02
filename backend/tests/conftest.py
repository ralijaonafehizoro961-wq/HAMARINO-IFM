import os
import pytest
from fastapi.testclient import TestClient

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('DATABASE_PATH',str(tmp_path/'test.sqlite3'))
    monkeypatch.setenv('ADMIN_API_KEY','test-admin-key-1234')
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    monkeypatch.delenv('GOOGLE_FACTCHECK_API_KEY',raising=False)
    from app.config import settings
    settings.cache_clear()
    from app.main import app
    with TestClient(app) as client:
        yield client
    settings.cache_clear()
