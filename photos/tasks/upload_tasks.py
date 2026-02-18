# photos/tasks/upload_tasks.py

from celery import shared_task
from io import BytesIO
from PIL import Image, ImageOps

from gallery.models import Photo
from photos.services.deduplication_service import DeduplicationService
from photos.services.upload_service import (
    read_storage_bytes,
    _calculate_sha256_bytes,
    _calculate_image_hashes,
    _extract_exif_taken_at,
)

@shared_task
def process_uploaded_photo(photo_id: int) -> bool:
    """
    업로드 후처리(무거운 작업):
    - storage에서 bytes 다시 읽기
    - PIL 디코딩 + EXIF 회전 보정
    - taken_at/width/height 저장
    - SHA256 + (p/d/a)hash 저장
    - exact duplicate 마킹(file_hash 기반)
    """
    photo = Photo.objects.get(id=photo_id)

    storage_name = photo.image.name  # ImageField니까 name이 key
    data = read_storage_bytes(storage_name)

    image = Image.open(BytesIO(data))
    image = ImageOps.exif_transpose(image)

    # 메타
    photo.width, photo.height = image.size
    photo.taken_at = _extract_exif_taken_at(image)

    # 해시
    photo.file_hash = _calculate_sha256_bytes(data)
    hashes = _calculate_image_hashes(image.convert("RGB"))
    photo.phash = hashes["phash"]
    photo.dhash = hashes["dhash"]
    photo.ahash = hashes["ahash"]

    photo.save(update_fields=[
        "width", "height", "taken_at",
        "file_hash", "phash", "dhash", "ahash",
        "updated_at"
    ])

    # exact duplicate 마킹
    DeduplicationService.check_exact_duplicate_and_mark(
        user=photo.user,
        photo=photo,
    )

    return True
