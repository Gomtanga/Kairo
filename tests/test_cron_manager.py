# [KAIRO] Tests for core.cron_manager.CronManager
import json
import os
import tempfile
import shutil
from unittest.mock import patch

import pytest

from core.cron_manager import CronManager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _mock_scheduler():
    """Mock BackgroundScheduler so no real scheduler process runs in any test."""
    with patch("core.cron_manager.BackgroundScheduler") as mock:
        yield mock


@pytest.fixture(autouse=True)
def _temp_paths():
    """Redirect CRON_JOBS_PATH / CRON_RESULTS_PATH to a temp directory so tests
    never touch the real production files and are completely isolated."""
    tmpdir = tempfile.mkdtemp()
    jobs_path = os.path.join(tmpdir, "cron_jobs.json")
    results_path = os.path.join(tmpdir, "cron_results.json")
    with (
        patch("core.cron_manager.CRON_JOBS_PATH", jobs_path),
        patch("core.cron_manager.CRON_RESULTS_PATH", results_path),
    ):
        yield jobs_path, results_path
    shutil.rmtree(tmpdir)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCronManager:

    # -- 1 ----------------------------------------------------------------
    def test_load_jobs_missing_file(self, _temp_paths):
        """When CRON_JOBS_PATH does not exist, self.jobs stays an empty dict."""
        jobs_path, _ = _temp_paths
        assert not os.path.exists(jobs_path)

        mgr = CronManager()
        assert mgr.jobs == {}

    # -- 2 ----------------------------------------------------------------
    def test_save_and_load_jobs(self, _temp_paths):
        """Jobs persisted via _save_jobs are recovered by a fresh CronManager."""
        jobs_path, _ = _temp_paths

        mgr1 = CronManager()
        sample = {
            "job_1": {
                "type": "static",
                "cron_expr": "0 9 * * 1",
                "task_name": "morning_report",
                "status": "active",
            },
        }
        mgr1.jobs = sample
        mgr1._save_jobs()

        assert os.path.exists(jobs_path)
        with open(jobs_path, encoding="utf-8") as f:
            assert json.load(f) == sample

        mgr2 = CronManager()
        assert mgr2.jobs == sample

    # -- 3 ----------------------------------------------------------------
    def test_load_results_missing_file(self, _temp_paths):
        """When CRON_RESULTS_PATH does not exist, self.results stays an empty dict."""
        _, results_path = _temp_paths
        assert not os.path.exists(results_path)

        mgr = CronManager()
        assert mgr.results == {}

    # -- 4 ----------------------------------------------------------------
    @pytest.mark.parametrize("expr", [
        "invalid",          # 1 part
        "* * * * * *",      # 6 parts
        "* * * *",          # 4 parts
        "",                 # 0 parts
        "a b c d e f g",    # 7 parts
    ])
    def test_add_static_cron_invalid_expr(self, expr):
        """add_static_cron returns False when cron_expr does not have exactly 5 parts."""
        mgr = CronManager()
        assert mgr.add_static_cron("test", expr, "Test", "") is False
        assert mgr.jobs == {}

    # -- 5 ----------------------------------------------------------------
    def test_list_crons(self):
        """After adding a job, list_crons returns it with full metadata."""
        mgr = CronManager()
        added = mgr.add_static_cron(
            "weekly_report", "0 9 * * 1", "Weekly Report", "Runs every Monday",
        )
        assert added is True

        crons = mgr.list_crons()
        assert len(crons) == 1
        entry = crons[0]
        assert entry["id"] == "weekly_report"
        assert entry["task_name"] == "Weekly Report"
        assert entry["task_description"] == "Runs every Monday"
        assert entry["type"] == "static"
        assert entry["status"] == "active"
        assert entry["cron_expr"] == "0 9 * * 1"

    # -- 6 ----------------------------------------------------------------
    def test_remove_cron(self):
        """A job can be added then removed; removing a non-existent job returns False."""
        mgr = CronManager()

        mgr.add_static_cron("job_A", "30 8 * * 1-5", "Weekday Job", "")
        assert len(mgr.list_crons()) == 1

        assert mgr.remove_cron("job_A") is True
        assert mgr.list_crons() == []

        assert mgr.remove_cron("job_A") is False
        assert mgr.remove_cron("never_added") is False
