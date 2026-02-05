# photos/tasks/import_photos.py
from celery import shared_task
from django.contrib.auth.models import User
from django.conf import settings
from photos.models import GoogleCredential, ImportJob
from gallery.models import Photo, Category
from photos.services.google_photos_service import GooglePhotosService
from photos.services.import_service import ImportService
import os


@shared_task(bind=True)
def import_google_photos_task(self, user_id, job_id, folder_id=None, dedupe=True, session_id=None):
    try:
        user = User.objects.get(id=user_id)
        job = ImportJob.objects.get(job_id=job_id)

        if not session_id:
            if hasattr(job, "picker_session_id") and job.picker_session_id:
                session_id = job.picker_session_id

        if not session_id:
            raise ValueError("session_id is required for Google Photos Picker import")

        ImportService.update_job_status(job, "RUNNING")

        google_cred = GoogleCredential.objects.get(user=user, is_active=True)

        unclassified_category, _ = Category.objects.get_or_create(
            user=user,
            name="분류 전",
            defaults={"category_key": None, "parent": None},
        )

        google_service = GooglePhotosService(google_cred)

        page_token = None
        all_items = []

        while True:
            result = google_service.get_photos(
                page_size=100,
                page_token=page_token,
                session_id=session_id,
            )
            items = result.get("items", [])
            all_items.extend(items)

            page_token = result.get("nextPageToken")
            if not page_token:
                break

        job.total_count = len(all_items)
        job.save(update_fields=["total_count"])

        for media_item in all_items:
            try:
                google_id = media_item.get("id")
                media_file = media_item.get("mediaFile") or {}
                filename = media_file.get("filename") or media_item.get("filename") or f"photo_{google_id}.jpg"

                if dedupe and google_id:
                    exists = Photo.objects.filter(
                        user=user,
                        google_id=google_id,
                        is_deleted=False,
                    ).exists()
                    if exists:
                        job.skipped_count += 1
                        job.save(update_fields=["skipped_count"])
                        continue

                media_subdir = f"photos/{user.id}"
                relative_path = f"{media_subdir}/{filename}"

                abs_dir = os.path.join(settings.MEDIA_ROOT, media_subdir)
                os.makedirs(abs_dir, exist_ok=True)

                abs_path = os.path.join(settings.MEDIA_ROOT, relative_path)

                google_service.download_photo(media_item, abs_path)

                Photo.objects.create(
                    user=user,
                    filename=filename,
                    image=relative_path,
                    url=relative_path,
                    file_hash="",
                    phash="",
                    dhash="",
                    source="GOOGLE",
                    google_id=google_id,
                    category=unclassified_category,
                )

                job.done_count += 1
                job.save(update_fields=["done_count"])

            except Exception as e:
                job.failed_count += 1
                job.save(update_fields=["failed_count"])
                print(f"Failed to import photo {media_item.get('id')}: {e}")
                continue

        ImportService.update_job_status(job, "DONE")

        return {
            "total": job.total_count,
            "done": job.done_count,
            "skipped": job.skipped_count,
            "failed": job.failed_count,
        }

    except Exception as e:
        job = ImportJob.objects.get(job_id=job_id)
        ImportService.update_job_status(job, "FAILED", error_message=str(e))
        raise
