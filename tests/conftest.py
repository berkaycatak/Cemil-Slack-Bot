"""
Pytest configuration ve fixtures.
"""

import sys
import types
from unittest.mock import MagicMock

# Agir 3rd-party bagimliliklar test ortaminda bulunmayabilir.
# conftest.py test modullerinden once yuklendiginden, burada
# eksik modulleri mock'layarak import zincirini kiyoruz.
_HEAVY_DEPS = [
    "sentence_transformers",
    "faiss",
    "apscheduler",
    "apscheduler.schedulers",
    "apscheduler.schedulers.background",
    "apscheduler.triggers",
    "apscheduler.triggers.cron",
    "apscheduler.triggers.interval",
    "langchain_text_splitters",
    "transformers",
]
for _mod in _HEAVY_DEPS:
    if _mod not in sys.modules:
        mock = MagicMock()
        # importlib.util.find_spec() icin __spec__ gerekli
        mock.__spec__ = types.ModuleType(_mod).__dict__.get("__spec__")
        sys.modules[_mod] = mock

import pytest
import os
import tempfile
import shutil
from pathlib import Path

# Test için geçici veritabanı
@pytest.fixture
def temp_db():
    """Geçici veritabanı oluşturur."""
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_cemil_bot.db")
    yield db_path
    # Cleanup
    if os.path.exists(db_path):
        os.remove(db_path)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def temp_knowledge_base():
    """Geçici knowledge base klasörü oluşturur."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Test için mock environment variables."""
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test-token")
    monkeypatch.setenv("SLACK_APP_TOKEN", "xapp-test-token")
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
    monkeypatch.setenv("ADMIN_CHANNEL_ID", "C123456")
    monkeypatch.setenv("SLACK_STARTUP_CHANNEL", "C123456")
