import pytest
from core.config import (
    KB_PATH, KB_BACKUP_PATH, KB_BACKUP_DIR,
    MAX_SESSIONS, LLM_TIMEOUT, LEVEL_THRESHOLDS
)


class TestConfig:
    def test_kb_path_exists(self):
        assert isinstance(KB_PATH, str)
        assert len(KB_PATH) > 0
        assert KB_PATH.endswith("kb.md")

    def test_kb_backup_path_exists(self):
        assert KB_BACKUP_PATH.endswith(".bak")

    def test_kb_backup_dir_exists(self):
        assert ".backups" in KB_BACKUP_DIR

    def test_max_sessions_is_positive_int(self):
        assert isinstance(MAX_SESSIONS, int)
        assert MAX_SESSIONS > 0

    def test_llm_timeout_positive(self):
        assert isinstance(LLM_TIMEOUT, int)
        assert LLM_TIMEOUT > 0

    def test_level_thresholds_structure(self):
        assert isinstance(LEVEL_THRESHOLDS, dict)
        for level in range(5):
            assert level in LEVEL_THRESHOLDS
            assert "interactions" in LEVEL_THRESHOLDS[level]
