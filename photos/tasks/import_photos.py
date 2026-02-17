# photos/tasks/import_photos.py

from celery import shared_task

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from photos.models import GoogleCredential, ImportJob
from gallery.models import Photo, Category

from photos.services.google_photos_service import GooglePhotosService
from photos.services.import_service import ImportService
from photos.services.upload_service import save_uploaded_file

import os
import tempfile


@shared_task(bind=True)
def import_google_photos_task(
    self,
    user_id,
    job_id,
    folder_id=None,
    dedupe=True,
    session_id=None
):
    job = None
    try:
        user = User.objects.get(id=user_id)
        job = ImportJob.objects.get(job_id=job_id)

        # picker session_id 복원
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

        # 1) picker session 기반으로 전체 item 수집
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

        # 2) 각 item 처리
        for media_item in all_items:
            try:
                google_id = media_item.get("id")
                media_file = media_item.get("mediaFile") or {}
                filename = (
                    media_file.get("filename")
                    or media_item.get("filename")
                    or (f"photo_{google_id}.jpg" if google_id else "photo.jpg")
                )

                # (A) google_id 기준 중복 스킵
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

                # (B) 기존 코드처럼 MEDIA_ROOT에 저장하지 않음
                # google_service.download_photo(media_item, abs_path)만 제공되는 상황을 고려해
                # 임시 파일(tmp)에 다운로드 → bytes 읽기 → save_uploaded_file로 Cloudinary 저장
                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1] or ".jpg") as tmp:
                    tmp_path = tmp.name

                try:
                    google_service.download_photo(media_item, tmp_path)

                    with open(tmp_path, "rb") as fp:
                        content = fp.read()

                    cf = ContentFile(content)
                    cf.name = filename  # ✅ save_uploaded_file이 원래 파일명을 meta["filename"]에 반영

                    meta = save_uploaded_file(user, cf)

                finally:
                    # 임시파일 제거
                    try:
                        os.remove(tmp_path)
                    except OSError:
                        pass

                # (C) SHA-256(file_hash) 기준 Exact 중복 방지 (google_id가 달라도 같은 파일이면 스킵 가능)
                # - 기존 로컬 업로드와 동일한 중복 기준으로 통일
                existing_by_hash = Photo.objects.filter(
                    user=user,
                    file_hash=meta["file_hash"],
                    is_deleted=False,
                ).first()

                if existing_by_hash:
                    # 방금 Cloudinary에 올린 리소스 정리
                    try:
                        if meta.get("storage_name"):
                            default_storage.delete(meta["storage_name"])
                    except Exception:
                        pass
                    try:
                        if meta.get("thumb_storage_name"):
                            default_storage.delete(meta["thumb_storage_name"])
                    except Exception:
                        pass

                    job.skipped_count += 1
                    job.save(update_fields=["skipped_count"])
                    continue

                # (D) DB 저장: image에는 storage key, url에는 절대 URL 저장 (Cloudinary 기준)
                Photo.objects.create(
                    user=user,
                    filename=meta["filename"],
                    image=meta["storage_name"],     # ✅ Cloudinary storage key
                    url=meta["url"],                # ✅ Cloudinary absolute URL

                    file_size=meta.get("file_size", 0),
                    file_hash=meta.get("file_hash", ""),
                    phash=meta.get("phash", ""),
                    dhash=meta.get("dhash", ""),
                    ahash=meta.get("ahash", ""),

                    width=meta.get("width"),
                    height=meta.get("height"),
                    taken_at=meta.get("taken_at"),

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
        # job 조회가 실패할 수도 있으니 안전하게 처리
        try:
            if job is None:
                job = ImportJob.objects.get(job_id=job_id)
            ImportService.update_job_status(job, "FAILED", error_message=str(e))
        except Exception:
            pass
        raise