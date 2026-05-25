# [KAIRO] Cron Manager - Static and dynamic cron job management
from datetime import datetime
from typing import Optional, Callable
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from core.config import CRON_MAX_RETRIES


class CronManager:
    """Manages static and dynamic cron jobs via APScheduler."""

    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.jobs: dict[str, dict] = {}  # job_id -> metadata
        self._started = False

    def start(self):
        """Start the scheduler."""
        if not self._started:
            self.scheduler.start()
            self._started = True

    def stop(self):
        """Stop the scheduler."""
        if self._started:
            self.scheduler.shutdown(wait=False)
            self._started = False

    def add_static_cron(
        self,
        job_id: str,
        cron_expr: str,
        task_name: str,
        task_description: str,
        callback: Optional[Callable] = None,
    ) -> bool:
        """Add a static (user-defined) cron job.

        Args:
            job_id: Unique identifier
            cron_expr: Cron expression (e.g., "0 9 * * *" for daily 9am)
            task_name: Human-readable name
            task_description: What the job does
            callback: Optional callable to execute
        """
        try:
            parts = cron_expr.split()
            if len(parts) != 5:
                return False

            trigger = CronTrigger(
                minute=parts[0],
                hour=parts[1],
                day=parts[2],
                month=parts[3],
                day_of_week=parts[4],
            )

            if callback:
                self.scheduler.add_job(
                    callback,
                    trigger=trigger,
                    id=job_id,
                    max_instances=1,
                    misfire_grace_time=60,
                )

            self.jobs[job_id] = {
                "type": "static",
                "cron_expr": cron_expr,
                "task_name": task_name,
                "task_description": task_description,
                "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "status": "active",
            }
            return True

        except Exception as e:
            return False

    def add_dynamic_cron(
        self,
        job_id: str,
        cron_expr: str,
        task_name: str,
        task_description: str,
        confidence: float = 0.0,
        callback: Optional[Callable] = None,
    ) -> bool:
        """Add a dynamic (agent-suggested) cron job."""
        try:
            parts = cron_expr.split()
            if len(parts) != 5:
                return False

            trigger = CronTrigger(
                minute=parts[0],
                hour=parts[1],
                day=parts[2],
                month=parts[3],
                day_of_week=parts[4],
            )

            if callback:
                self.scheduler.add_job(
                    callback,
                    trigger=trigger,
                    id=job_id,
                    max_instances=1,
                    misfire_grace_time=60,
                )

            self.jobs[job_id] = {
                "type": "dynamic",
                "cron_expr": cron_expr,
                "task_name": task_name,
                "task_description": task_description,
                "confidence": confidence,
                "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "status": "active",
            }
            return True

        except Exception:
            return False

    def remove_cron(self, job_id: str) -> bool:
        """Remove a cron job."""
        if job_id in self.jobs:
            try:
                self.scheduler.remove_job(job_id)
            except Exception:
                pass
            del self.jobs[job_id]
            return True
        return False

    def pause_cron(self, job_id: str) -> bool:
        """Pause a cron job."""
        if job_id in self.jobs:
            try:
                self.scheduler.pause_job(job_id)
                self.jobs[job_id]["status"] = "paused"
                return True
            except Exception:
                return False
        return False

    def resume_cron(self, job_id: str) -> bool:
        """Resume a paused cron job."""
        if job_id in self.jobs:
            try:
                self.scheduler.resume_job(job_id)
                self.jobs[job_id]["status"] = "active"
                return True
            except Exception:
                return False
        return False

    def list_crons(self) -> list[dict]:
        """List all cron jobs."""
        return [
            {"id": job_id, **metadata}
            for job_id, metadata in self.jobs.items()
        ]

    def get_cron(self, job_id: str) -> Optional[dict]:
        """Get a specific cron job's metadata."""
        if job_id in self.jobs:
            return {"id": job_id, **self.jobs[job_id]}
        return None
