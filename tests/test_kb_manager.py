# [KAIRO] Unit tests for KBManager – basic CRUD plus advanced operations
import os
import re
import shutil
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from core.kb_manager import KBManager


class TestKBManager:
    """Unit tests for KBManager — read/write/backup/template."""

    @pytest.fixture(autouse=True)
    def setup(self, monkeypatch):
        self.tmpdir = tempfile.mkdtemp()
        self.kb_path = os.path.join(self.tmpdir, "test_kb.md")
        self.backup_dir = os.path.join(self.tmpdir, "backups")
        monkeypatch.setattr("core.kb_manager.KB_BACKUP_DIR", self.backup_dir)
        monkeypatch.setattr("core.kb_manager.KB_MAX_INTERACTION_LOGS", 3)
        yield
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    # -- read / write / backup / template -----------------------------------

    def test_write_empty_raises_valueerror(self):
        """write('') should raise ValueError."""
        mgr = KBManager(kb_path=self.kb_path)
        with pytest.raises(ValueError, match="empty content"):
            mgr.write("")

    def test_write_valid_content(self):
        """write valid content, read it back, verify match."""
        mgr = KBManager(kb_path=self.kb_path)
        mgr.write("# Hello World")
        content = mgr.read()
        assert content == "# Hello World"

    def test_backup_creates_timestamped_file(self):
        """write triggers a timestamped backup in KB_BACKUP_DIR."""
        mgr = KBManager(kb_path=self.kb_path)
        mgr.write("# Original")
        mgr.write("# Updated")
        backups = os.listdir(self.backup_dir)
        assert len(backups) >= 1
        assert any(f.startswith("kb_") and f.endswith(".md.bak") for f in backups)

    def test_read_auto_creates_template(self):
        """read() auto-creates template when file is missing."""
        assert not os.path.exists(self.kb_path)
        mgr = KBManager(kb_path=self.kb_path)
        content = mgr.read()
        assert content.startswith("# Kairo Knowledge Base")
        assert "## 👤 User Profile" in content
        assert "## 📚 Projects" in content
        assert "## 📊 Growth Log" in content
        assert os.path.exists(self.kb_path)


class TestKBManagerUpdateSection:
    """Tests for KBManager.update_section."""

    @pytest.fixture(autouse=True)
    def setup(self, monkeypatch):
        self.tmpdir = tempfile.mkdtemp()
        self.kb_path = os.path.join(self.tmpdir, "test_kb.md")
        self.backup_dir = os.path.join(self.tmpdir, "backups")
        monkeypatch.setattr("core.kb_manager.KB_BACKUP_DIR", self.backup_dir)
        yield
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _mgr(self, content: str = None) -> KBManager:
        mgr = KBManager(kb_path=self.kb_path)
        if content:
            mgr.write(content)
        return mgr

    def test_replaces_existing_section(self):
        """update_section replaces the content of an existing section."""
        content = (
            "# KB\n"
            "\n"
            "## 👤 User Profile\n"
            "- name: Old\n"
            "- major: CS\n"
            "\n"
            "## 📚 Projects\n"
            "- Project A\n"
        )
        mgr = self._mgr(content)
        new_section = "## 👤 User Profile\n- name: New Name\n- major: Physics"
        mgr.update_section("## 👤 User Profile", new_section)

        updated = mgr.read()
        assert "- name: New Name" in updated
        assert "- name: Old" not in updated
        assert "Project A" in updated

    def test_appends_when_section_missing(self):
        """update_section appends when the section header does not exist."""
        mgr = self._mgr("# KB\n")
        mgr.update_section("## 👤 User Profile", "## 👤 User Profile\n- name: New")
        updated = mgr.read()
        assert "## 👤 User Profile" in updated
        assert "- name: New" in updated

    def test_creates_backup(self):
        """update_section triggers a backup before writing."""
        mgr = self._mgr("## 👤 User Profile\n-old\n")
        mgr.update_section("## 👤 User Profile", "## 👤 User Profile\n-new\n")
        backups = os.listdir(self.backup_dir)
        assert len(backups) >= 1

    def test_respects_header_level(self):
        """update_section replaces from header to next same-level header (### is not ## boundary)."""
        content = (
            "# KB\n"
            "## 📚 Projects\n"
            "- Proj A\n"
            "### 📚 Projects\n"
            "- Sub project\n"
        )
        mgr = self._mgr(content)
        mgr.update_section("## 📚 Projects", "## 📚 Projects\n- Proj B")
        updated = mgr.read()
        assert "Proj A" not in updated
        assert "Proj B" in updated
        # ### 📚 Projects (level 3) is not recognized as a ##-level boundary,
        # so it is included in the replaced section and Sub project is gone
        assert "Sub project" not in updated


class TestKBManagerAppendToSection:
    """Tests for KBManager.append_to_section."""

    @pytest.fixture(autouse=True)
    def setup(self, monkeypatch):
        self.tmpdir = tempfile.mkdtemp()
        self.kb_path = os.path.join(self.tmpdir, "test_kb.md")
        self.backup_dir = os.path.join(self.tmpdir, "backups")
        monkeypatch.setattr("core.kb_manager.KB_BACKUP_DIR", self.backup_dir)
        yield
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _mgr(self, content: str = None) -> KBManager:
        mgr = KBManager(kb_path=self.kb_path)
        if content:
            mgr.write(content)
        return mgr

    def test_appends_after_existing_header(self):
        """append_to_section adds text right after the section header."""
        content = (
            "# KB\n"
            "## 📊 Growth Log\n"
            "### Interaction 1\n"
            "- date: 1\n"
        )
        mgr = self._mgr(content)
        mgr.append_to_section("## 📊 Growth Log", "### Interaction 2\n- date: 2")
        updated = mgr.read()
        assert "### Interaction 2" in updated
        assert "### Interaction 1" in updated

    def test_creates_section_when_missing(self):
        """append_to_section creates the section if it does not exist."""
        mgr = self._mgr("# KB\n")
        mgr.append_to_section("## 🧩 Missing Section", "some content")
        updated = mgr.read()
        assert "## 🧩 Missing Section" in updated
        assert "some content" in updated

    def test_creates_backup(self):
        """append_to_section triggers a backup."""
        mgr = self._mgr("## 📊 Growth Log\n")
        mgr.append_to_section("## 📊 Growth Log", "### Interaction 1\n")
        backups = os.listdir(self.backup_dir)
        assert len(backups) >= 1


class TestKBManagerIncrementInteraction:
    """Tests for KBManager.increment_interaction."""

    @pytest.fixture(autouse=True)
    def setup(self, monkeypatch):
        self.tmpdir = tempfile.mkdtemp()
        self.kb_path = os.path.join(self.tmpdir, "test_kb.md")
        self.backup_dir = os.path.join(self.tmpdir, "backups")
        monkeypatch.setattr("core.kb_manager.KB_BACKUP_DIR", self.backup_dir)
        monkeypatch.setattr("core.kb_manager.KB_MAX_INTERACTION_LOGS", 3)
        yield
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _mgr(self, content: str = None) -> KBManager:
        mgr = KBManager(kb_path=self.kb_path)
        if content:
            mgr.write(content)
        return mgr

    def test_initial_count_is_one(self):
        """increment_interaction starts at 1 for a fresh KB with no interactions."""
        mgr = self._mgr("# KB\n## 📊 Growth Log\n")
        count = mgr.increment_interaction()
        assert count == 1
        content = mgr.read()
        assert "### Interaction 1" in content

    def test_sequential_increment(self):
        """increment_interaction increments from existing count."""
        mgr = self._mgr(
            "# KB\n"
            "## 📊 Growth Log\n"
            "### Interaction 5\n"
            "- date: earlier\n"
        )
        count = mgr.increment_interaction()
        assert count == 6
        content = mgr.read()
        assert "### Interaction 6" in content
        assert "### Interaction 5" in content

    def test_creates_growth_log_section(self):
        """increment_interaction creates the Growth Log section if missing."""
        mgr = self._mgr("# KB Only\n")
        count = mgr.increment_interaction()
        assert count == 1
        content = mgr.read()
        assert "## 📊 Growth Log" in content
        assert "### Interaction 1" in content

    def test_trims_oldest_entries(self):
        """increment_interaction trims OLDEST entries (tail) when exceeding limit."""
        # Growth Log is newest-first: append_to_section inserts at top.
        # Create entries newest-first (10=newest at top, 1=oldest at tail).
        # With 10 existing + 1 new = 11, trimming removes the oldest (tail).
        entries = "".join(
            f"### Interaction {i}\n- date: {i}\n" for i in range(10, 0, -1)
        )
        mgr = self._mgr(f"# KB\n## 📊 Growth Log\n{entries}")
        count = mgr.increment_interaction()
        assert count == 11
        content = mgr.read()
        # Interaction 11 is newest (at top), should be KEPT
        assert "### Interaction 11" in content
        # Interaction 10, 9 should also be KEPT (still within limit)
        assert "### Interaction 10" in content
        # Interaction 1 is oldest (at tail), should be REMOVED by trimming
        # Use exact match to avoid false positive from "Interaction 11"
        assert "\n### Interaction 1\n" not in content

    def test_returns_int(self):
        """increment_interaction returns an integer."""
        mgr = self._mgr("# KB\n## 📊 Growth Log\n")
        assert isinstance(mgr.increment_interaction(), int)


class TestKBManagerCompress:
    """Tests for KBManager.compress and related helpers."""

    @pytest.fixture(autouse=True)
    def setup(self, monkeypatch):
        self.tmpdir = tempfile.mkdtemp()
        self.kb_path = os.path.join(self.tmpdir, "test_kb.md")
        self.backup_dir = os.path.join(self.tmpdir, "backups")
        monkeypatch.setattr("core.kb_manager.KB_BACKUP_DIR", self.backup_dir)
        monkeypatch.setattr("core.kb_manager.KB_MAX_INTERACTION_LOGS", 3)
        yield
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _mgr(self, content: str = None) -> KBManager:
        mgr = KBManager(kb_path=self.kb_path)
        if content:
            mgr.write(content)
        return mgr

    def test_no_need(self):
        """compress returns (False, msg) when token count is below threshold."""
        mgr = self._mgr("# Small KB\n## 📊 Growth Log\n### Interaction 1\n- date: now\n")
        success, msg = mgr.compress()
        assert success is False
        assert "압축이 필요하지 않습니다" in msg

    def test_no_growth_log(self):
        """compress returns (False, msg) when there is no Growth Log section."""
        mgr = self._mgr("# Just a profile\n## 👤 User Profile\n- name: Tester\n")
        with patch.object(mgr, "needs_compression", return_value=True):
            success, msg = mgr.compress()
        assert success is False
        assert "Growth Log 섹션이 없어" in msg

    def test_too_few_entries(self):
        """compress returns (False, msg) when there are 3 or fewer entries."""
        content = (
            "# KB\n## 📊 Growth Log\n"
            "### Interaction 1\n- date: a\n"
            "### Interaction 2\n- date: b\n"
            "### Interaction 3\n- date: c\n"
        )
        mgr = self._mgr(content)
        with patch.object(mgr, "needs_compression", return_value=True):
            success, msg = mgr.compress()
        assert success is False
        assert "충분히 적어" in msg

    def test_basic_summary_fallback(self):
        """compress uses basic summary when no llm_client is given."""
        # Entries are newest-first. Interaction 4 = newest (kept), 1 = oldest (summarized).
        content = (
            "# KB\n## 📊 Growth Log\n"
            "### Interaction 4\n- date: 2025-01-04\n- type: user_chat\n"
            "- detail: Final entry with enough text to be compressible\n"
            "- detail: The summary will be much shorter than these entries\n"
            "### Interaction 3\n- date: 2025-01-03\n- type: system\n"
            "- detail: System generated entry with lots of verbose text\n"
            "- detail: More system details that are not critical\n"
            "### Interaction 2\n- date: 2025-01-02\n- type: user_chat\n"
            "- detail: Another long entry with substantial text content here\n"
            "- detail: More detailed information about the second interaction\n"
            "- detail: Additional context that takes up many lines\n"
            "### Interaction 1\n- date: 2025-01-01\n- type: user_chat\n"
            "- detail: Lorem ipsum dolor sit amet consectetur adipiscing elit\n"
            "- detail: Sed do eiusmod tempor incididunt ut labore et dolore magna\n"
            "- detail: Ut enim ad minim veniam quis nostrud exercitation ullamco\n"
            "- detail: Duis aute irure dolor in reprehenderit in voluptate velit\n"
            "- detail: Excepteur sint occaecat cupidatat non proident sunt culpa\n"
            "- result: completed successfully with no errors\n"
        )
        mgr = self._mgr(content)
        with patch.object(mgr, "needs_compression", return_value=True):
            success, msg = mgr.compress()

        assert success is True, f"compress failed: {msg}"
        assert "압축 완료" in msg
        updated = mgr.read()
        # Newest 3 (4, 3, 2) should be KEPT
        assert "### Interaction 4" in updated
        assert "### Interaction 3" in updated
        assert "### Interaction 2" in updated
        # Oldest (1) should be summarized
        assert "### Interaction 1" not in updated
        assert "요약" in updated or "summary" in updated.lower()

    def test_with_llm_summary(self):
        """compress uses LLM summary when llm_client is provided."""
        content = (
            "# KB\n## 📊 Growth Log\n"
            "### Interaction 1\n- date: 2025-01-01\n- type: user_chat\n"
            "- detail: " + "x" * 100 + "\n"
            "- detail: " + "x" * 100 + "\n"
            "- detail: " + "x" * 100 + "\n"
            "- detail: " + "x" * 100 + "\n"
            "- detail: " + "x" * 100 + "\n"
            "- detail: " + "x" * 100 + "\n"
            "- detail: " + "x" * 100 + "\n"
            "### Interaction 2\n- date: 2025-01-02\n- type: user_chat\n"
            "- detail: " + "x" * 100 + "\n"
            "- detail: " + "x" * 100 + "\n"
            "### Interaction 3\n- date: 2025-01-03\n- type: system\n"
            "- detail: " + "x" * 100 + "\n"
            "- detail: " + "x" * 100 + "\n"
            "### Interaction 4\n- date: 2025-01-04\n- type: user_chat\n"
            "- detail: " + "x" * 100 + "\n"
            "- detail: " + "x" * 100 + "\n"
        )
        mgr = self._mgr(content)

        mock_llm = MagicMock()
        mock_llm.chat.return_value = {
            "content": "LLM generated summary of 3 old entries covering various interactions.",
            "tool_calls": [],
            "reasoning": "",
        }

        with patch.object(mgr, "needs_compression", return_value=True):
            success, msg = mgr.compress(llm_client=mock_llm)

        assert success is True, f"compress failed: {msg}"
        assert "압축 완료" in msg
        mock_llm.chat.assert_called_once()
        updated = mgr.read()
        assert "LLM generated summary" in updated

    def test_llm_fallback_on_error(self):
        """compress falls back to basic summary when LLM call raises."""
        content = (
            "# KB\n## 📊 Growth Log\n"
            "### Interaction 1\n- date: 2025-01-01\n- type: user_chat\n"
            "- detail: " + "x" * 100 + "\n"
            "- detail: " + "x" * 100 + "\n"
            "- detail: " + "x" * 100 + "\n"
            "- detail: " + "x" * 100 + "\n"
            "- detail: " + "x" * 100 + "\n"
            "### Interaction 2\n- date: 2025-01-02\n- type: user_chat\n"
            "- detail: " + "x" * 100 + "\n"
            "- detail: " + "x" * 100 + "\n"
            "### Interaction 3\n- date: 2025-01-03\n- type: system\n"
            "- detail: " + "x" * 100 + "\n"
            "- detail: " + "x" * 100 + "\n"
            "### Interaction 4\n- date: 2025-01-04\n- type: user_chat\n"
            "- detail: " + "x" * 100 + "\n"
            "- detail: " + "x" * 100 + "\n"
        )
        mgr = self._mgr(content)

        mock_llm = MagicMock()
        mock_llm.chat.side_effect = Exception("API Error")

        with patch.object(mgr, "needs_compression", return_value=True):
            success, msg = mgr.compress(llm_client=mock_llm)

        assert success is True, f"compress failed: {msg}"
        assert "압축 완료" in msg
        updated = mgr.read()
        assert "summary" in updated.lower() or "요약" in updated

    def test_success_path(self):
        """compress succeeds with 4+ verbose entries reducing token count."""
        content = (
            "# " + "x" * 500 + "\n"
            "## 📊 Growth Log\n"
            "### Interaction 1\n- date: a\n- type: x\n"
            "- detail: " + "y" * 200 + "\n"
            "- detail: " + "y" * 200 + "\n"
            "### Interaction 2\n- date: b\n- type: x\n"
            "- detail: " + "y" * 200 + "\n"
            "- detail: " + "y" * 200 + "\n"
            "### Interaction 3\n- date: c\n- type: x\n"
            "- detail: " + "y" * 200 + "\n"
            "- detail: " + "y" * 200 + "\n"
            "### Interaction 4\n- date: d\n- type: x\n"
            "- detail: " + "y" * 200 + "\n"
            "- detail: " + "y" * 200 + "\n"
        )
        mgr = self._mgr(content)
        with patch.object(mgr, "needs_compression", return_value=True):
            success, msg = mgr.compress()
        assert success is True, f"compress failed: {msg}"


class TestKBManagerHelpers:
    """Tests for KBManager private/helper methods."""

    @pytest.fixture(autouse=True)
    def setup(self, monkeypatch):
        self.tmpdir = tempfile.mkdtemp()
        self.kb_path = os.path.join(self.tmpdir, "test_kb.md")
        self.backup_dir = os.path.join(self.tmpdir, "backups")
        monkeypatch.setattr("core.kb_manager.KB_BACKUP_DIR", self.backup_dir)
        yield
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    # -- _parse_interaction_count -------------------------------------------

    def test_parse_count_empty(self):
        """_parse_interaction_count returns 0 when no interactions exist."""
        assert KBManager._parse_interaction_count("") == 0
        assert KBManager._parse_interaction_count("# No interactions here\n") == 0

    def test_parse_count_finds_max(self):
        """_parse_interaction_count returns the highest interaction number."""
        content = "### Interaction 1\n### Interaction 5\n### Interaction 3\n"
        assert KBManager._parse_interaction_count(content) == 5

    # -- _sanitize_summary --------------------------------------------------

    def test_sanitize_truncates(self):
        """_sanitize_summary truncates text to max_chars."""
        text = "a" * 300
        result = KBManager._sanitize_summary(text, max_chars=50)
        assert len(result) <= 53
        assert result.endswith("...")

    def test_sanitize_escapes_hashes(self):
        """_sanitize_summary escapes # to prevent accidental headings."""
        result = KBManager._sanitize_summary("Topic #1 and #2")
        assert "\\#1" in result or "\\#2" in result

    # -- _basic_summary -----------------------------------------------------

    def test_basic_summary_format(self):
        """_basic_summary produces expected format with dates and types."""
        mgr = KBManager(kb_path=self.kb_path)
        entries = [
            "### Interaction 1\n- date: 2025-01-01\n- type: user_chat",
            "### Interaction 2\n- date: 2025-01-02\n- type: system",
        ]
        result = mgr._basic_summary(entries)
        assert "📋 요약 (압축)" in result
        assert "2개 Growth Log" in result
        assert "user_chat" in result
        assert "system" in result
        assert "2025-01-01" in result
        assert "2025-01-02" in result

    # -- estimate_tokens / needs_compression ---------------------------------

    def test_estimate_tokens(self):
        """estimate_tokens returns int based on length / 3.5."""
        mgr = KBManager(kb_path=self.kb_path)
        tokens = mgr.estimate_tokens("a" * 350)
        assert tokens == 100

    def test_estimate_tokens_from_file(self):
        """estimate_tokens without arg reads from the current KB file."""
        mgr = KBManager(kb_path=self.kb_path)
        mgr.write("a" * 350)
        tokens = mgr.estimate_tokens()
        assert tokens == 100

    def test_needs_compression_true(self):
        """needs_compression returns True when token count exceeds threshold."""
        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.setattr("core.kb_manager.KB_MAX_TOKEN_RATIO", 0.01)
        mgr = KBManager(kb_path=self.kb_path)
        mgr.write("x" * 100_000)
        assert mgr.needs_compression() is True
        monkeypatch.undo()

    def test_needs_compression_false(self):
        """needs_compression returns False for small content."""
        mgr = KBManager(kb_path=self.kb_path)
        mgr.write("Small content")
        assert mgr.needs_compression() is False

    # -- restore_backup -----------------------------------------------------

    def test_restore_backup_exists(self):
        """restore_backup returns True when backup exists."""
        mgr = KBManager(kb_path=self.kb_path)
        # Simulate a backup file at the backup path
        mgr.write("# Original")
        os.makedirs(self.backup_dir, exist_ok=True)
        backup_file = os.path.join(self.backup_dir, "kb_test.md.bak")
        with open(backup_file, "w", encoding="utf-8") as f:
            f.write("# Backup content")

        # Make the backup_path point to this file
        mgr.backup_path = backup_file
        assert mgr.restore_backup() is True

    def test_restore_backup_missing(self):
        """restore_backup returns False when no backup file exists."""
        mgr = KBManager(kb_path=self.kb_path)
        mgr.kb_path = os.path.join(self.tmpdir, "nonexistent.md")
        mgr.backup_path = os.path.join(self.tmpdir, "nonexistent.md.bak")
        assert mgr.restore_backup() is False

    # -- _trim_growth_log ---------------------------------------------------

    def test_trim_under_limit(self):
        """_trim_growth_log does nothing when entry count is within limit."""
        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.setattr("core.kb_manager.KB_MAX_INTERACTION_LOGS", 5)
        content = (
            "# KB\n## 📊 Growth Log\n"
            "### Interaction 1\n- date: 1\n"
            "### Interaction 2\n- date: 2\n"
            "### Interaction 3\n- date: 3\n"
        )
        mgr = KBManager(kb_path=self.kb_path)
        mgr.write(content)
        mgr._trim_growth_log()
        updated = mgr.read()
        assert "### Interaction 1" in updated
        monkeypatch.undo()

    def test_trim_removes_oldest(self):
        """_trim_growth_log removes OLDEST entries (tail) when over limit."""
        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.setattr("core.kb_manager.KB_MAX_INTERACTION_LOGS", 3)
        # Growth Log is newest-first: Interaction 5 = newest (at top), 1 = oldest (at tail)
        content = (
            "# KB\n## 📊 Growth Log\n"
            "### Interaction 5\n- date: 5\n"
            "### Interaction 4\n- date: 4\n"
            "### Interaction 3\n- date: 3\n"
            "### Interaction 2\n- date: 2\n"
            "### Interaction 1\n- date: 1\n"
        )
        mgr = KBManager(kb_path=self.kb_path)
        mgr.write(content)
        mgr._trim_growth_log()
        updated = mgr.read()
        # Newest (5, 4, 3) should be KEPT
        assert "### Interaction 5" in updated
        assert "### Interaction 4" in updated
        assert "### Interaction 3" in updated
        # Oldest (2, 1) should be REMOVED
        assert "### Interaction 2" not in updated
        assert "### Interaction 1" not in updated
        monkeypatch.undo()

    def test_trim_no_section(self):
        """_trim_growth_log does nothing when Growth Log section is missing."""
        mgr = KBManager(kb_path=self.kb_path)
        mgr.write("# No growth log here\n")
        mgr._trim_growth_log()  # Should not raise
