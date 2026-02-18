from celery import shared_task
from io import BytesIO
from PIL import Image, ImageOps

from gallery.models import Photo
from photos.services.deduplication_service import DeduplicationService
from photos.services.upload_service import (
    read_storage_bytes,
    _calculate_image_hashes,
    _extract_exif_taken_at,
)


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def process_uploaded_photo(self, photo_id: int) -> bool:
    try:
        photo = Photo.objects.get(id=photo_id)
    except Photo.DoesNotExist:
        return False

    # ✅ 이미 완료면 재처리 안 함
    if photo.processing_status == "DONE":
        return True

    # 시작 상태
    Photo.objects.filter(id=photo_id).update(processing_status="PROCESSING", processing_error=None)

    try:
        storage_name = photo.image.name
        data = read_storage_bytes(storage_name)

        image = Image.open(BytesIO(data))
        image = ImageOps.exif_transpose(image)

        width, height = image.size
        taken_at = _extract_exif_taken_at(image)

        hashes = _calculate_image_hashes(image.convert("RGB"))

        photo.width = width
        photo.height = height
        photo.taken_at = taken_at
        photo.phash = hashes["phash"]
        photo.dhash = hashes["dhash"]
        photo.ahash = hashes["ahash"]

        if not photo.file_hash:
            import hashlib
            sha256 = hashlib.sha256()
            sha256.update(data)
            photo.file_hash = sha256.hexdigest()

        photo.processing_status = "DONE"
        photo.processing_error = None
        photo.save(update_fields=[
            "width", "height", "taken_at",
            "file_hash", "phash", "dhash", "ahash",
            "processing_status", "processing_error",
            "updated_at",
        ])

        DeduplicationService.check_exact_duplicate_and_mark(
            user=photo.user,
            photo=photo,
        )

        return True

    except Exception as e:
        Photo.objects.filter(id=photo_id).update(
            processing_status="FAILED",
            processing_error=str(e)[:2000],
        )
        raise self.retry(exc=e)