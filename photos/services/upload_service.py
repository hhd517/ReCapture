# photos/services/upload_service.py

import os
import uuid
import hashlib
from datetime import datetime
from typing import Dict

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import UploadedFile

from PIL import Image, ExifTags
import imagehash


# =========================
# Hash Utils (bytes 기반)
# =========================

def _calculate_sha256_bytes(data: bytes) -> str:
    sha256 = hashlib.sha256()
    sha256.update(data)
    return sha256.hexdigest()


def _calculate_image_hashes(image: Image.Image) -> Dict[str, str]:
    return {
        "phash": str(imagehash.phash(image)),
        "dhash": str(imagehash.dhash(image)),
        "ahash": str(imagehash.average_hash(image)),
    }


# =========================
# Image Utils
# =========================

def _extract_exif_taken_at(image: Image.Image):
    try:
        exif = image._getexif()
        if not exif:
            return None

        for tag, value in exif.items():
            tag_name = ExifTags.TAGS.get(tag)
            if tag_name == "DateTimeOriginal":
                return datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
    except Exception:
        return None
    return None


def _create_thumbnail(image: Image.Image, size=(300, 300)) -> Image.Image:
    thumb = image.copy()
    thumb.thumbnail(size)
    return thumb


def _pil_to_jpeg_bytes(image: Image.Image, quality: int) -> bytes:
    """PIL Image -> JPEG bytes"""
    from io import BytesIO
    buf = BytesIO()
    image.save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


# =========================
# Main Service
# =========================

def save_uploaded_file(user, uploaded_file: UploadedFile) -> Dict:
    """
    업로드된 이미지 파일을 Cloudinary(default_storage)에 저장하고 메타데이터 추출
    """

    user_id = user.id
    original_name = uploaded_file.name

    # 1) 원본 파일 bytes 확보 (업로드/구글 가져오기 모두 대응)
    file_bytes = uploaded_file.read()
    if hasattr(uploaded_file, "seek"):
        uploaded_file.seek(0)

    # 2) PIL 로드 + RGB 통일
    from io import BytesIO
    image = Image.open(BytesIO(file_bytes))
    image = image.convert("RGB")

    width, height = image.size
    file_size = len(file_bytes)

    # 3) 해시/메타
    file_hash = _calculate_sha256_bytes(file_bytes)
    image_hashes = _calculate_image_hashes(image)
    taken_at = _extract_exif_taken_at(image)

    # 4) 저장 파일명(확장자/실데이터 불일치 방지 위해 jpg 고정)
    unique_name = f"{uuid.uuid4().hex}.jpg"

    # Cloudinary에 저장될 “경로(폴더)”를 이름에 포함시켜 관리
    photo_key = f"photos/{user_id}/{unique_name}"
    thumb_key = f"thumbnails/{user_id}/{unique_name}"

    # 5) 원본/썸네일을 JPEG bytes로 만들어 storage에 저장
    photo_bytes = _pil_to_jpeg_bytes(image, quality=95)
    thumb_image = _create_thumbnail(image)
    thumb_bytes = _pil_to_jpeg_bytes(thumb_image, quality=85)

    default_storage.save(photo_key, ContentFile(photo_bytes))
    default_storage.save(thumb_key, ContentFile(thumb_bytes))

    # 6) URL은 storage가 만들어주는 “실제 접근 가능한 URL” 사용
    photo_url = default_storage.url(photo_key)
    thumb_url = default_storage.url(thumb_key)

    return {
        "filename": original_name,        # 원래 파일명 유지(표시용)
        "url": photo_url,                 # ✅ Cloudinary URL
        "thumb_url": thumb_url,           # ✅ Cloudinary URL
        "file_size": file_size,
        "width": width,
        "height": height,
        "taken_at": taken_at,
        "file_hash": file_hash,
        "phash": image_hashes["phash"],
        "dhash": image_hashes["dhash"],
        "ahash": image_hashes["ahash"],
    }