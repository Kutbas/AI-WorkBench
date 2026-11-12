"""后台任务管理：job（一次提交）→ 多个子任务，状态机 + JSON 持久化。

状态：子任务 pending → running → done/failed；job 汇总 running → done/partial/failed。
服务重启时从磁盘恢复：终态原样保留，非终态标记 interrupted（结果仍可查看已生成部分）。
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime
from pathlib import Path

_TERMINAL = {"done", "failed", "interrupted"}


def _safe_name(name: str, fallback: str = "task") -> str:
    """任务/文件名安全化：只留字母数字下划线连字符和中文，其余换下划线。"""
    s = re.sub(r"[^\w\u4e00-\u9fff-]+", "_", (name or "").strip()).strip("_")
    return s or fallback


class TaskManager:
    def __init__(self, jobs_dir: Path):
        self.jobs_dir = jobs_dir
        self._jobs: dict[str, dict] = {}

    # ---------- 持久化 ----------

    def load_all(self) -> None:
        """启动恢复：读回所有 job；非终态的标记 interrupted。"""
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        for path in sorted(self.jobs_dir.glob("*/*.json")):
            try:
                job = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as e:
                print(f"[taskmanager] 跳过损坏的任务文件 {path}: {e}")
                continue
            if job.get("status") not in _TERMINAL:
                job["status"] = "interrupted"
                for t in job.get("tasks", []):
                    if t.get("status") not in _TERMINAL:
                        t["status"] = "interrupted"
                        if not t.get("error"):
                            t["error"] = "服务重启，任务中断"
                self._persist(job)
            self._jobs[job["id"]] = job

    def _persist(self, job: dict) -> None:
        d = self.jobs_dir / job["type"]
        d.mkdir(parents=True, exist_ok=True)
        path = d / f"{job['id']}.json"
        path.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---------- job 生命周期 ----------

    def create(self, job_type: str, params: dict, task_names: list[str]) -> dict:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        job_id = f"{job_type}_{ts}_{uuid.uuid4().hex[:6]}"
        job = {
            "id": job_id,
            "type": job_type,
            "status": "running",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "params": params,
            "tasks": [{"name": n, "status": "pending", "error": None} for n in task_names],
        }
        self._jobs[job_id] = job
        self._persist(job)
        return job

    def get(self, job_id: str) -> dict | None:
        return self._jobs.get(job_id)

    def list(self, job_type: str, limit: int = 20) -> list[dict]:
        jobs = [j for j in self._jobs.values() if j["type"] == job_type]
        jobs.sort(key=lambda j: j["created_at"], reverse=True)
        return jobs[:limit]

    def start_task(self, job_id: str, idx: int) -> None:
        self._mutate_task(job_id, idx, status="running", error=None)

    def finish_task(self, job_id: str, idx: int, ok: bool, error: str | None = None, **result) -> None:
        fields = {"status": "done" if ok else "failed", "error": error}
        fields.update(result)
        self._mutate_task(job_id, idx, **fields)

    def _mutate_task(self, job_id: str, idx: int, **fields) -> None:
        job = self._jobs.get(job_id)
        if job is None or not (0 <= idx < len(job["tasks"])):
            return
        job["tasks"][idx].update(fields)
        self._recompute(job)
        self._persist(job)

    def _recompute(self, job: dict) -> None:
        statuses = [t["status"] for t in job["tasks"]]
        if any(s in ("pending", "running") for s in statuses):
            job["status"] = "running"
        elif all(s == "done" for s in statuses):
            job["status"] = "done"
        elif all(s == "failed" for s in statuses):
            job["status"] = "failed"
        else:
            job["status"] = "partial"

    # ---------- 工具 ----------

    @staticmethod
    def safe_name(name: str, fallback: str = "task") -> str:
        return _safe_name(name, fallback)
