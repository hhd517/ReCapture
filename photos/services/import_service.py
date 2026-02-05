# photos/services/import_service.py
import uuid
from datetime import datetime


class ImportService:
    @staticmethod
    def generate_job_id():
        return f"imp_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def calculate_progress(job):
        total = job.total_count or 0
        done = job.done_count or 0
        skipped = job.skipped_count or 0
        failed = job.failed_count or 0

        return {
            "total": total,
            "done": done,
            "skipped": skipped,
            "failed": failed,
        }

    @staticmethod
    def update_job_status(job, status, error_message=None):
        job.status = status

        if status == "RUNNING" and not job.started_at:
            job.started_at = datetime.now()

        if status in ["DONE", "FAILED"]:
            job.completed_at = datetime.now()

        if error_message:
            job.error_message = error_message

        job.save()
        return job
