import pytest
import os
import tempfile
import shutil
from core.kb_manager import KBManager


class TestKBManager:
    """Unit tests for KBManager."""

    @pytest.fixture(autouse=True)
    def setup(self, monkeypatch):
        self.tmpdir = tempfile.mkdtemp()
        self.kb_path = os.path.join(self.tmpdir, "test_kb.md")
        self.backup_dir = os.path.join(self.tmpdir, "backups")
        monkeypatch.setattr("core.kb_manager.KB_BACKUP_DIR", self.backup_dir)
        yield
        shutil.rmtree(self.tmpdir, ignore_errors=True)

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
