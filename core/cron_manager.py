# [KAIRO] Cron Manager - Static and dynamic cron job management
import json
import os
from datetime import datetime
from typing import Optional, Callable
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from core.config import CRON_MAX_RETRIES

CRON_JOBS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cron_jobs.json")
CRON_RESULTS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cron_results.json")


class CronManager:

    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.jobs: dict[str, dict] = {}
        self.results: dict[str, dict] = {}
        self._started = False
        self._load_jobs()
        self._load_results()

    def _load_jobs(self):
        if os.path.exists(CRON_JOBS_PATH):
            try:
                with open(CRON_JOBS_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for job_id, meta in data.items():
                    self.jobs[job_id] = meta
            except Exception:
                pass

    def _save_jobs(self):
        try:
            with open(CRON_JOBS_PATH, "w", encoding="utf-8") as f:
                json.dump(self.jobs, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _load_results(self):
        if os.path.exists(CRON_RESULTS_PATH):
            try:
                with open(CRON_RESULTS_PATH, "r", encoding="utf-8") as f:
                    self.results = json.load(f)
            except Exception:
                self.results = {}

    def _save_results(self):
        try:
            with open(CRON_RESULTS_PATH, "w", encoding="utf-8") as f:
                json.dump(self.results, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def get_result(self, job_id: str) -> Optional[dict]:
        return self.results.get(job_id)

    def execute_job(self, job_id: str) -> dict:
        if job_id not in self.jobs:
            return {"status": "error", "message": f"잡 '{job_id}'을 찾을 수 없습니다."}

        job = self.jobs[job_id]
        task_name = job.get("task_name", job_id)
        task_description = job.get("task_description", "")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        result = {
            "status": "success",
            "job_id": job_id,
            "task_name": task_name,
            "executed_at": now,
            "message": f"'{task_name}' 작업이 실행되었습니다.",
        }

        if task_description:
            result["task_description"] = task_description

        try:
            from core.llm_client import LLMClient
            llm = LLMClient()
            prompt = (
                f"다음 예약 작업을 지금 실행합니다. 작업에 맞는 결과를 생성해주세요.\n\n"
                f"작업 이름: {task_name}\n"
                f"작업 설명: {task_description}\n"
                f"실행 시간: {now}\n\n"
                f"위 작업에 대한 결과를 간결하게 제공해주세요."
            )
            llm_response = llm.chat([{"role": "user", "content": prompt}])
            result["llm_response"] = llm_response
        except Exception as e:
            result["llm_response"] = f"LLM 실행 오류: {e}"

        self.results[job_id] = result
        self._save_results()
        return result

    def start(self):
        if not self._started:
            self.scheduler.start()
            self._started = True
            self._restore_scheduled_jobs()

    def _restore_scheduled_jobs(self):
        for job_id, meta in self.jobs.items():
            if meta.get("status") != "active":
                continue
            if self.scheduler.get_job(job_id) is not None:
                continue
            parts = meta.get("cron_expr", "").split()
            if len(parts) != 5:
                continue
            try:
                trigger = CronTrigger(
                    minute=parts[0],
                    hour=parts[1],
                    day=parts[2],
                    month=parts[3],
                    day_of_week=parts[4],
                )
                self.scheduler.add_job(
                    self.execute_job,
                    trigger=trigger,
                    id=job_id,
                    args=[job_id],
                    max_instances=1,
                    misfire_grace_time=60,
                )
            except Exception:
                pass

    def stop(self):
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
            else:
                self.scheduler.add_job(
                    self.execute_job,
                    trigger=trigger,
                    id=job_id,
                    args=[job_id],
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
            self._save_jobs()
            return True

        except Exception:
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
            else:
                self.scheduler.add_job(
                    self.execute_job,
                    trigger=trigger,
                    id=job_id,
                    args=[job_id],
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
            self._save_jobs()
            return True

        except Exception:
            return False

    def remove_cron(self, job_id: str) -> bool:
        if job_id in self.jobs:
            try:
                self.scheduler.remove_job(job_id)
            except Exception:
                pass
            del self.jobs[job_id]
            self._save_jobs()
            return True
        return False

    def pause_cron(self, job_id: str) -> bool:
        if job_id in self.jobs:
            try:
                self.scheduler.pause_job(job_id)
            except Exception:
                pass
            self.jobs[job_id]["status"] = "paused"
            self._save_jobs()
            return True
        return False

    def resume_cron(self, job_id: str) -> bool:
        if job_id in self.jobs:
            try:
                self.scheduler.resume_job(job_id)
            except Exception:
                pass
            self.jobs[job_id]["status"] = "active"
            self._save_jobs()
            return True
        return False

    def list_crons(self) -> list[dict]:
        return [
            {"id": job_id, **metadata}
            for job_id, metadata in self.jobs.items()
        ]

    def get_cron(self, job_id: str) -> Optional[dict]:
        if job_id in self.jobs:
            return {"id": job_id, **self.jobs[job_id]}
        return None
