# classification/services/job_store.py
import uuid
from django.core.cache import cache

JOB_TTL = 60 * 60  # 1 hour

def new_job(total: int) -> str:
    job_id = uuid.uuid4().hex
    cache.set(
        f"job:{job_id}",
        {
            "status": "queued",  # queued | running | done | failed
            "total": int(total),
            "done": 0,
            "failed": 0,
            "current_photo_id": None,
            "message": "대기중...",
            "failed_photo_ids": [],
        },
        timeout=JOB_TTL,
    )
    return job_id

def get_job(job_id: str) -> dict | None:
    return cache.get(f"job:{job_id}")

def update_job(job_id: str, **kwargs) -> None:
    key = f"job:{job_id}"
    job = cache.get(key) or {}
    job.update(kwargs)
    cache.set(key, job, timeout=JOB_TTL)

def inc_done(job_id: str) -> None:
    key = f"job:{job_id}"
    job = cache.get(key) or {}
    job["done"] = int(job.get("done", 0)) + 1
    cache.set(key, job, timeout=JOB_TTL)

def inc_failed(job_id: str, photo_id: int | None = None) -> None:
    key = f"job:{job_id}"
    job = cache.get(key) or {}
    job["failed"] = int(job.get("failed", 0)) + 1
    if photo_id is not None:
        lst = job.get("failed_photo_ids", [])
        lst.append(int(photo_id))
        job["failed_photo_ids"] = lst
    cache.set(key, job, timeout=JOB_TTL)