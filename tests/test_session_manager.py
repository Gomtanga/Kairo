# [KAIRO] Unit tests for SessionManager
import json
import os
import tempfile
import shutil
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from core.session_manager import SessionManager
from core.config import MAX_SESSIONS


class TestSessionManager:
    """Tests for core.session_manager.SessionManager."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.patcher = patch("core.session_manager.SESSIONS_DIR", self.tmpdir)
        self.patcher.start()

    def teardown_method(self):
        self.patcher.stop()
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _fake_now(seconds: int = 0) -> datetime:
        """Return a fixed datetime with a controllable second offset."""
        return datetime(2024, 1, 1, 12, 0, 0) + timedelta(seconds=seconds)

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------

    def test_create_session(self):
        """Creating a session returns a dict with expected keys."""
        fake_time = self._fake_now()
        with patch("core.session_manager.datetime") as mock_dt:
            mock_dt.now.return_value = fake_time

            session = SessionManager.create_session("My Test")

        assert isinstance(session, dict)
        assert session["id"] == "20240101_120000"
        assert session["title"] == "My Test"
        assert session["created_at"] == "2024-01-01 12:00:00"
        assert session["updated_at"] == "2024-01-01 12:00:00"
        assert session["messages"] == []

    def test_create_session_default_title(self):
        """When no title is given, a default title is generated."""
        fake_time = self._fake_now()
        with patch("core.session_manager.datetime") as mock_dt:
            mock_dt.now.return_value = fake_time

            session = SessionManager.create_session()

        assert session["title"] == "새 대화 20240101_120000"

    def test_list_sessions(self):
        """list_sessions returns all sessions sorted newest first."""
        counter = [0]

        def inc_now():
            counter[0] += 1
            return self._fake_now(counter[0])

        with patch("core.session_manager.datetime") as mock_dt:
            mock_dt.now = inc_now

            s1 = SessionManager.create_session("First")
            s2 = SessionManager.create_session("Second")

        sessions = SessionManager.list_sessions()

        assert len(sessions) == 2
        assert sessions[0]["id"] == s2["id"]
        assert sessions[0]["title"] == "Second"
        assert sessions[1]["id"] == s1["id"]
        assert sessions[1]["title"] == "First"

    def test_delete_session(self):
        """Deleting a session removes it from listing."""
        fake_time = self._fake_now()
        with patch("core.session_manager.datetime") as mock_dt:
            mock_dt.now.return_value = fake_time

            session = SessionManager.create_session("To Delete")

        assert len(SessionManager.list_sessions()) == 1

        SessionManager.delete_session(session["id"])
        assert len(SessionManager.list_sessions()) == 0

    def test_delete_nonexistent_session(self):
        """Deleting a session that does not exist does not raise."""
        SessionManager.delete_session("nonexistent_000000")

    def test_add_message(self):
        """add_message appends a message to the session."""
        fake_time = self._fake_now()
        with patch("core.session_manager.datetime") as mock_dt:
            mock_dt.now.return_value = fake_time

            session = SessionManager.create_session("Chat")

        SessionManager.add_message(session["id"], "user", "Hello!")
        SessionManager.add_message(session["id"], "assistant", "Hi there!")

        loaded = SessionManager.load_session(session["id"])
        assert len(loaded["messages"]) == 2
        assert loaded["messages"][0] == {"role": "user", "content": "Hello!"}
        assert loaded["messages"][1] == {"role": "assistant", "content": "Hi there!"}

    def test_add_message_to_nonexistent_session(self):
        """Adding a message to a missing session does nothing (no crash)."""
        SessionManager.add_message("no_such_session", "user", "ping")

    def test_max_sessions_enforcement(self):
        """Creating beyond MAX_SESSIONS evicts the oldest session."""
        # Pre-populate MAX_SESSIONS session files directly
        for i in range(MAX_SESSIONS):
            sid = f"20240101_{i:06d}"
            session = {
                "id": sid,
                "title": f"prefill-{i}",
                "created_at": f"2024-01-01 00:00:{i:02d}",
                "updated_at": f"2024-01-01 00:00:{i:02d}",
                "messages": [],
            }
            with open(os.path.join(self.tmpdir, f"{sid}.json"), "w", encoding="utf-8") as f:
                json.dump(session, f, ensure_ascii=False, indent=2)

        assert len(SessionManager.list_sessions()) == MAX_SESSIONS

        # Create one more session (triggers _cleanup_old_sessions)
        extra = SessionManager.create_session("extra")
        sessions = SessionManager.list_sessions()

        assert len(sessions) == MAX_SESSIONS
        # The newly created session should be present
        assert extra["id"] in [s["id"] for s in sessions]

    def test_load_session_returns_none_for_missing(self):
        """load_session returns None when session does not exist."""
        result = SessionManager.load_session("does_not_exist")
        assert result is None

    def test_fork_session(self):
        """fork_session creates a new session with messages up to fork_from_index."""
        fake_time = self._fake_now()
        with patch("core.session_manager.datetime") as mock_dt:
            mock_dt.now.return_value = fake_time
            session = SessionManager.create_session("Original")

        SessionManager.add_message(session["id"], "user", "msg0")
        SessionManager.add_message(session["id"], "user", "msg1")
        SessionManager.add_message(session["id"], "user", "msg2")

        with patch("core.session_manager.datetime") as mock_dt:
            mock_dt.now.return_value = self._fake_now(99)
            forked = SessionManager.fork_session(session["id"], fork_from_index=1)

        assert forked is not None
        assert forked["title"] == "[FORK] Original"
        assert len(forked["messages"]) == 2
        assert forked["messages"][0]["content"] == "msg0"
        assert forked["messages"][1]["content"] == "msg1"
        assert forked["id"] == "20240101_120139"  # 12:00:00 + 99s = 12:01:39

        original = SessionManager.load_session(session["id"])
        assert len(original["messages"]) == 3

    def test_fork_session_missing_source(self):
        """fork_session returns None when source session does not exist."""
        result = SessionManager.fork_session("nonexistent", 0)
        assert result is None

    def test_update_title(self):
        """update_title changes the session title."""
        fake_time = self._fake_now()
        with patch("core.session_manager.datetime") as mock_dt:
            mock_dt.now.return_value = fake_time
            session = SessionManager.create_session("Old Title")

        SessionManager.update_title(session["id"], "New Title")
        loaded = SessionManager.load_session(session["id"])

        assert loaded["title"] == "New Title"

    def test_update_title_missing_session(self):
        """update_title on nonexistent session does not raise."""
        SessionManager.update_title("no_such", "anything")
